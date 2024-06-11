from collections import defaultdict
import datetime
import json
import os
import sys
from typing import Dict, List

sys.path.append(os.path.join(os.path.dirname(__file__), '../'))

from common import logger
from hit_manager import HITManager

_LOGGER = logger.get_logger(__name__)


# must have value less than or equal to 100
MAX_LIST_HIT_RESULTS = 100


def log_hit(hit):
    """Prints a summary of the hits returned by the mtruk API"""
    assignments_pending = hit["NumberOfAssignmentsPending"]
    assignments_available = hit["NumberOfAssignmentsAvailable"]
    assignments_completed = hit["NumberOfAssignmentsCompleted"]
    _LOGGER.info(
        f"\nHit {hit['HITId']} - Status {hit['HITStatus']} - " +
        f"\nAssignments pending {assignments_available}" if assignments_available > 0 else "" +
        f"\nAssignments pending {assignments_pending}" if assignments_pending > 0 else "" +
        f"\nAssignments pending {assignments_completed}" if assignments_completed > 0 else "" +
        f"\n Creation time {hit['CreationTime']} - Expiration time {hit['Expiration']}"
    )


class MinecraftEvalHitManager(HITManager):

    # We need to detect the hits that have not been reviewed but are expired.
    # If they expired since the script is running, we can free the instance
    def get_open_hit_ids_by_status(self, hit_type: str, remove_expired=True) -> Dict[str, List[str]]:
        """

        Returns:
            Dict[str, List[str]]: List of open hit ids.
        """
        partial_results = self.mturk_client.list_hits(MaxResults=MAX_LIST_HIT_RESULTS)
        done = partial_results['NumResults'] == 0
        pagination_token = partial_results['NextToken']

        selected_hits = defaultdict(list)
        while not done:
            for hit in partial_results['HITs']:
                hit_id = hit['HITId']
                if 'RequesterAnnotation' in hit:
                    if json.loads(hit['RequesterAnnotation'])['hit_type'] != hit_type:
                        continue
                log_hit(hit)

                if self.is_hit_expired(hit):
                    _LOGGER.info(f'Hit {hit_id} has expired.')
                    # If it does not have any completed assignments, delete it.
                    if (remove_expired and hit['NumberOfAssignmentsCompleted'] == 0 and
                            hit['HITStatus'] in ['Reviewing', 'Reviewable']):
                        _LOGGER.info(f'Deleting hit {hit_id} with no assignments that expired'
                                     f' at {hit["Expiration"]}')
                        # Free instance!
                        self.delete_hit(hit_id=hit_id)
                        selected_hits['deleted'].append(hit_id)
                    else:
                        # If it has assignments, mark it as reviewed so it is not returned again.
                        if hit['HITStatus'] == 'Reviewable':
                            self.mturk_client.update_hit_review_status(HITId=hit_id, Revert=False)
                            selected_hits['to_close'].append(hit_id)
                            _LOGGER.info(f'Closing hit {hit_id} that expired at {hit["Expiration"]}')
                    if hit_id in self.session_open_hits:
                        self.session_open_hits.remove(hit_id)
                    continue

                # Check hit has not been reviewed or discarded.
                # When the HIT assignment is processed, in method `close_assignment`, the is
                # is marked as "Reviewing".
                if hit['HITStatus'] in ['Assignable', 'Reviewable', 'Unassignable']:
                    print(f"HIT {hit_id} open")
                    selected_hits['open'].append(hit['HITId'])

            partial_results = self.mturk_client.list_hits(
                MaxResults=MAX_LIST_HIT_RESULTS, NextToken=pagination_token)
            if 'NextToken' in partial_results:
                pagination_token = partial_results['NextToken']
            else:
                pagination_token = None
            done = partial_results['NumResults'] == 0

        # Add the hits opened by this script that may not have been processed by mturk yet
        selected_hits['open'] = list(set(selected_hits['open']).union(self.session_open_hits))

        _LOGGER.info(
            f"{len(selected_hits['open'])} open hits of type {hit_type} returned. " +
            (f"{len(selected_hits['to_close'])} expired with assignments hits to close. "
                if len(selected_hits['to_close']) > 0 else "") +
            (f"{len(selected_hits['deleted'])} expired hits without assignments deleted."
                if len(selected_hits['deleted']) > 0 else ""))
        return dict(selected_hits)

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
            hit_id = hit['HITId']

            if self.is_hit_expired(hit):
                _LOGGER.info(f'Hit {hit_id} has expired.')
                # If it does not have any assignments, delete it.
                if remove_expired and hit['NumberOfAssignmentsCompleted'] == 0:
                    _LOGGER.info(f'Deleting hit {hit_id} with no assignments that expired'
                                 f' at {hit["Expiration"]}')
                    self.delete_hit(HITId=hit_id)
                else:
                    # A hit becomes Reviewable when all workers have submitted answers to a hit
                    # If it has assignments, mark it as reviewed so it is not returned again.
                    if hit['HITStatus'] == 'Reviewable':
                        # Change state to Reviewing
                        self.mturk_client.update_hit_review_status(HITId=hit_id, Revert=False)
                # No matter the status, we don't consider it open anymore
                if hit_id in self.session_open_hits:
                    self.session_open_hits.remove(hit_id)
                continue

            # Check hit has not been reviewed or discarded
            if hit['HITStatus'] in ['Assignable', 'Reviewable', 'Unassignable']:
                selected_hits.append(hit_id)

        # Add the hits opened by this script that may not have been processed by mturk yet
        selected_hits = list(set(selected_hits).union(self.session_open_hits))

        _LOGGER.info(f"{len(selected_hits)} open hits of type {hit_type} returned")
        return selected_hits

    def notify_worker(self, worker_id, error_messages):
        message = ('Hello! \n\n It appears to be a problem with your HIT submission. ' +
            f'The mistakes found are: \n\n{error_messages}\n\n'
            'We will still pay you for this hit as we believe it might be a misunderstanding. '
            'We are aware it is a complex task, and we ask you to read carefully the instructions. '
            'Any feedback to improve them is welcomed! \n\n'
            'We thank you for your submission, however, if we notice more mistakes, '
            'we will, unfortunately, disqualify you from our task.'
        )
        self.mturk_client.notify_workers(
            Subject='Problem with your HIT submission: "IGLU - Play Minecraft game!"',
            MessageText=message, WorkerIds=[worker_id]
        )

    def notify_rejection(self, worker_id, error_messages):
        message = ('Hello! \n\n It appears to be a problem with your HIT submission. '
            f'The mistakes found are: \n\n{error_messages}\n\n'
            'We have an uncommon amount of malicious workers attempting this task. '
            'As a result, your assignment has been rejected and you have been blocked. '
            'If you consider this a mistake and it is clear in the submitted hit your answer '
            'is correct, please reply to us and we will evaluate the case and revert the '
            'rejection within 24hs. \n\n'
            'We apologize if this has caused you troubles, we never follow such drastic approach '
            'in our tasks, but this is a particular type of HIT that people are exploiting.'
        )
        self.mturk_client.notify_workers(
            Subject='Problem with your HIT submission: "IGLU - Play Minecraft game!"',
            MessageText=message, WorkerIds=[worker_id]
        )

    def close_assignment(self, assignment, qualification=True, error_message=""):
        """Approve or not the assignment based on its qualification."""

        if qualification == False:
            self.notify_rejection(assignment['WorkerId'], error_message)
            self.mturk_client.reject_assignment(
                AssignmentId=assignment['AssignmentId'],
                RequesterFeedback=error_message
            )
            self.block_worker(assignment['WorkerId'], error_message)
        else:
            if len(error_message) > 2:
                self.notify_worker(assignment['WorkerId'], error_message)
            # Always approve
            self.mturk_client.approve_assignment(
                AssignmentId=assignment['AssignmentId'], OverrideRejection=False)

        # Set "HITStatus" to "Reviewed" because all hits have only one assignment.
        self.mturk_client.update_hit_review_status(HITId=assignment['HitId'], Revert=False)

        if assignment['HitId'] in self.session_open_hits:
            self.session_open_hits.remove(assignment['HitId'])
        _LOGGER.info(
            f"Assignment {assignment['AssignmentId']} for hit {assignment['HitId']} closed.")

    def block_worker(self, worker_id, reason):
        _LOGGER.warning(f"Blocking worker {worker_id} for reason {reason}")
        self.mturk_client.create_worker_block(WorkerId=worker_id, Reason=reason)

    @staticmethod
    def is_hit_expired(hit_dict):
        # 1800 is the assignment duration in seconds. Even if the hit expires, a worker
        # may be able to use the join codes for the next 1800 seconds. We don't want to
        # delete the hit until we are absolutely sure the join code has expired and it is safe
        # to release the agent instance.
        # TODO remove the magic number and use the correct value from the hit config.
        delay = 0
        if (hit_dict['NumberOfAssignmentsPending'] > 0
            or hit_dict['NumberOfAssignmentsCompleted'] > 0):
            # There was at least one accepted assignment
            delay = 1800
        return datetime.datetime.now().timestamp() >= hit_dict['Expiration'].timestamp() + delay
