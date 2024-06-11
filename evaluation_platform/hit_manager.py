"""Function to create HITs with a given layouts.
"""
import boto3
import datetime
import json
import xmltodict

from string import Template
from typing import Any, Callable, Dict, List, Optional

from common import logger

_LOGGER = logger.get_logger(__name__)


class TemplateRenderer:
    """Abstract class to represent a template renderer.

    Every template will have its own variables to fill, which are captured
    by the kwargs parameter in function render_template.

    By creating new classes for different templates, it is possible to keep track
    of which template is used for each hit.
    """
    def __init__(self, template_filepath: str = 'templates') -> None:
        self.template_filepath = template_filepath

    def render_template(self, **kwargs):
        with open(self.template_filepath, 'r') as template_file:
            template = Template(template_file.read())
        return template.substitute(**kwargs)


class HITManager:

    def __init__(self, mturk_endpoint: str,
                 aws_access_key: str, aws_secret_key: str, max_hits: int = 99,
                 verification_function: Optional[Callable[[Dict[str, str]], bool]] = None,
                 **kwargs) -> None:
        self.mturk_client = boto3.client(
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
            service_name='mturk',
            region_name='us-east-1',
            endpoint_url=mturk_endpoint,
        )
        self.max_hits = max_hits
        # Save the open hits to know when to stop the collection. More hits may be open
        # from previous runs, and will be completed by this script.
        self.session_open_hits = set()
        if verification_function is None:
            self.verification_function = lambda x: True
        else:
            self.verification_function = verification_function

    def create_hit(
            self, rendered_template, hit_type: str = '', hit_lifetime_seconds=3600,
            max_assignments=1, keywords: str = 'iglu',
            auto_approval_delay_seconds: int = 3600, reward: str = "0.80",
            assignment_duration_in_seconds: int = 480,
            title: str = 'random title', description: str = 'random description',
            qualification_type_id: str = None,
            qualification_country_codes: Optional[List[str]] = None,
            **kwargs) -> str:

        self.assignment_duration_in_seconds = assignment_duration_in_seconds

        qualifiers = []
        if qualification_type_id is not None:
            qualifiers.append({
                'QualificationTypeId': qualification_type_id,
                'Comparator': 'GreaterThan',
                'IntegerValues': [86],
                'ActionsGuarded': 'PreviewAndAccept'
            })
        if qualification_country_codes is not None:
            # Recommended values US and CA
            qualifiers.append({
                'QualificationTypeId': '00000000000000000071',
                'Comparator': 'In',
                'LocaleValues': [{'Country': country} for country in qualification_country_codes],
                'ActionsGuarded': 'DiscoverPreviewAndAccept'
            })

        # Require previous hit acceptance of 85%
        qualifiers.append({
            'QualificationTypeId': '000000000000000000L0',
            'Comparator': 'GreaterThan',
            'IntegerValues': [95],
            'ActionsGuarded': 'DiscoverPreviewAndAccept'
        })
        # Require to have more than 100 hits approved. Avoid bot accounts
        qualifiers.append({
            'QualificationTypeId': '00000000000000000040',
            'Comparator': 'GreaterThan',
            'IntegerValues': [500],
            'ActionsGuarded': 'DiscoverPreviewAndAccept'
        })

        hit = self.mturk_client.create_hit(
            LifetimeInSeconds=hit_lifetime_seconds,  # 604800
            MaxAssignments=max_assignments,
            Keywords=keywords,
            AutoApprovalDelayInSeconds=auto_approval_delay_seconds,
            Reward=reward,
            AssignmentDurationInSeconds=assignment_duration_in_seconds,
            Title=title,
            Description=description,
            Question=rendered_template,
            RequesterAnnotation=json.dumps({'hit_type': hit_type}),
            QualificationRequirements=qualifiers
        )
        hit_id = hit['HIT']['HITId']
        _LOGGER.info(f'HIT created with Id {hit_id}')
        self.session_open_hits.add(hit_id)
        return hit_id

    def get_open_hit_ids(self, hit_type: str, remove_expired=False) -> List[str]:
        """Get hit that are not expired nor reviewed, and with this @hit_type.

        Returns:
            List[str]: List of open hit ids.
        """
        # TODO use pagination string
        hit_dict = self.mturk_client.list_hits(MaxResults=self.max_hits)['HITs']
        selected_hits = []
        for hit in hit_dict:
            if 'RequesterAnnotation' in hit:
                if json.loads(hit['RequesterAnnotation'])['hit_type'] != hit_type:
                    continue

            if self.is_hit_expired(hit):
                # If it does not have any assignments, complete it.
                if remove_expired and hit['NumberOfAssignmentsCompleted'] == 0:
                    self.delete_hit(hit_id=hit['HITId'])
                continue

            # Check hit has not been reviewed or discarded
            if hit['HITStatus'] in ['Assignable', 'Reviewable', 'Unassignable']:
                selected_hits.append(hit['HITId'])

        # Add the hits opened by this script that may not have been processed by mturk yet
        selected_hits = list(set(selected_hits).union(self.session_open_hits))

        _LOGGER.info(f"{len(selected_hits)} open hits of type {hit_type} returned")
        return selected_hits

    @staticmethod
    def is_hit_expired(hit_dict):
        return datetime.datetime.now().timestamp() >= hit_dict['Expiration'].timestamp()

    def complete_open_assignments(self, hit_ids: List[str]) -> Dict[str, Any]:
        """Get a list of the Assignments that have been submitted for all open hits.

        Reviews and completes the assignments, returning the answers as a dictionary.

        Args:
            hit_ids (List[str]): A list of hit ids to search for assignments and complete.

        Returns:
            dict: Dictionary from hit ids to responses of the assignments for that hit.
            If there is more than one assignment for the HIT, only the value of the last valid
            one is retrieved.
            The values are dictionaries with the results from each assignment. They contain
            the specific keys
                * `WorkerId`
                * `Answer` the content of the original mturk client response under keys
                    ["QuestionFormAnswers"]["Answer"]
                * `IsHitQualified`, the result of applying `self.verification_function`
                    on the previous field.
        """
        results = {}

        for hit_id in hit_ids:
            # Get a list of the Assignments that have been submitted
            submitted_assignments = self.mturk_client.list_assignments_for_hit(
                HITId=hit_id,
                AssignmentStatuses=['Submitted']
            )
            if submitted_assignments['NumResults'] == 0:
                continue

            assignments = submitted_assignments['Assignments']
            # Retrieve the attributes for each Assignment
            for assignment in assignments:
                # assignment contains keys WorkerId and AssingmentId, among others
                assignment['HitId'] = hit_id
                assignment['Answer'] = self._parse_xml_response(assignment['Answer'])
                # If qualification
                qualification, error_message = self.verification_function(assignment)
                assignment['IsHITQualified'] = qualification
                results[hit_id] = assignment
                self.close_assignment(assignment, qualification, error_message)
        return results

    @staticmethod
    def _parse_xml_response(xml_answer: str):
        """Parses xml answers from Mturk assignment dict returned by boto3 api.

        Returns:
            A dictionary with the extracted data under keys ['QuestionFormAnswers']['Answer'].
        """
        return xmltodict.parse(xml_answer)['QuestionFormAnswers']['Answer']

    def delete_hit(self, hit_id: str):
        try:
            self.mturk_client.delete_hit(HITId=hit_id)
        except:
            _LOGGER.warning(f'Unable to delete hit {hit_id}. '
                            'Most likely because it is in incorrect state.')

        if hit_id in self.session_open_hits:
            self.session_open_hits.remove(hit_id)

    def close_assignment(self, assignment, qualification=True, error_message=""):
        """Approve or not the assignment based on its qualification, and delete the hit.

        Current implementation approves all assignments, and relies on hits having a single
        assignment each.
        """
        self.mturk_client.approve_assignment(
            AssignmentId=assignment['AssignmentId'],
            OverrideRejection=False
        )

        # We can delete hit because all hits have only one assignment.
        self.delete_hit(assignment['HitId'])
        _LOGGER.info(f"Assignment {assignment['AssignmentId']} and {assignment['HitId']} closed.")
