import html
import xmltodict
import boto3
import json
import pandas as pd
import os
import csv
import argparse
import ast
from urllib.parse import quote
from datetime import datetime
from string import Template


access_key = os.getenv("AWS_ACCESS_KEY_ID_LIT")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY_LIT")
sas = os.getenv("AZURE_SAS")
dirname = os.path.dirname(__file__)

create_qualification_test_a = False #Tested: QT for Architect has been created, id below
create_qualification_test_b = False #Tested: QT for Builder has been created, id below
create_hits_in_production = False
get_results = False
create_hit = True
test_ids = False

environments = {
        "production": {
            "endpoint": "https://mturk-requester.us-east-1.amazonaws.com",
            "preview": "https://www.mturk.com/mturk/preview"
        },
        "sandbox": {
            "endpoint": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
            "preview": "https://workersandbox.mturk.com/mturk/preview"
        },
}
mturk_environment = environments["production"] if create_hits_in_production else environments["sandbox"]

mturk = boto3.client(
        aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_environment['endpoint'],
)

print(mturk.get_account_balance()['AvailableBalance'])


#For Testing
#System inputs
game_id = 'b49-a4-iglu-26-1624451367231'
structure_id = 'B49-A4-IGLU-26-1624451367231'
screenshot_view = 'north'
screenshot_id = 'target-structures/multiview/B49-A4-IGLU-26-1624451367231'
#User Inputs (need html.escape)
previous_instruction = 'I dont know what is going on' 
previous_instruction = 'Put 5 red blocks to the center'
answer = 'No, it should be two'
question = 'Are you sure it should be 5?'
#instruction = 'Put 5 red block in the middle'
instruction = 'I find the "any vs some" rules really frustrating and it seems only native speakers have the intuition of whats right. Ive read that "any" is generally used in questions but then "some" can be used in questions when the speaker expects a positive answer. If I say "have you got some paper for the printer?", is there any subtle difference from "have you got any paper for the printer?" Ive also heard that theres little difference between "do you need any help?" and "do you need some help?", which makes it even more confusing.'
prev_step = 1
current_step = 2
screenshotPath = ''


#Tested
#builder-initial
#builder-normal
#builder-answer-cq
#architect-answer-cq
#architect-initial


#Specify Type of HIT
type_hit = 'old-builder-normal'

if type_hit =='architect-cq':
   input = Template(open(os.path.join(dirname,'input/architect-cq.xml'), 'r').read()).substitute(structureId=structure_id, 
   screenshotView=screenshot_view,
   prevBuilderScreenshotPath = screenshot_id, previousInstr = html.escape(previous_instruction), question = html.escape(question))
elif type_hit == 'architect-normal':
     input = Template(open(os.path.join(dirname,'input/architect-normal.xml'), 'r').read()).substitute(structureId=structure_id, 
     prevBuilderScreenshotPath = screenshot_view)   
elif type_hit == 'builder-cq':
     input = Template(open(os.path.join(dirname,'input/builder-cq.xml'), 'r').read()).substitute(gameId=game_id, 
     screenshotId = screenshot_id, 
     instruction= html.escape(instruction), clarifyingQuestion = html.escape(question), answer = html.escape(answer), 
     prevStep = html.escape(prev_step), currentStep = html.escape(current_step), screenshotView = html.escape(screenshot_view))
elif type_hit == 'builder-normal': 
     input = Template(open(os.path.join(dirname,'input/builder-normal.xml'), 'r').read()).substitute(
         instruction = html.escape(instruction),
         gameId = html.escape(game_id), 
         prevStep = prev_step, 
         currentStep = current_step, 
         screenshotPath = "/builder-data/{}/step{}_".format(html.escape(game_id), prev_step),
         screenshotView = html.escape(screenshot_view))
elif type_hit == 'old-builder-normal': 
     input = Template(open(os.path.join(dirname,'input/old-builder-normal.xml'), 'r').read()).substitute(
         instruction = html.escape(instruction),
         gameId = html.escape(game_id),
         sas=sas)                 


if create_qualification_test_a:
        qual_response = mturk.create_qualification_type(
                        Name='Qualification test to qualify as an Architect in Minecraft Game 11111',
                        Keywords='test, qualification, sample, minecraft, iglu',
                        Description='This is Qualification test to perform architect role in collaborative Minecraft game',
                        QualificationTypeStatus='Active',
                        Test=open(os.path.join(dirname,'input/architect-qualification-questions.xml'), 'r').read(),
                        AnswerKey=open(os.path.join(dirname,'input/architect-qualification-answers.xml'), 'r').read(),
                        TestDurationInSeconds=300)
        print('QualificationType architect: '+qual_response['QualificationType']['QualificationTypeId'])
        #QualificationType architect: 3F97VQZTZ36ANTIH9STV6NGP8XZUHP

elif create_qualification_test_b:
        qual_response = mturk.create_qualification_type(
                        Name='Qualification test to qualify as a Builder in Minecraft Game 1111',
                        Keywords='test, qualification, sample, minecraft, iglu',
                        Description='This is a brief ',
                        QualificationTypeStatus='Active',
                        Test=open(os.path.join(dirname,'input/builder-qualification-questions.xml'), 'r').read(),
                        AnswerKey=open(os.path.join(dirname,'input/builder-qualification-answers.xml'), 'r').read(),
                        TestDurationInSeconds=300)
        print('QualificationType Builder '+qual_response['QualificationType']['QualificationTypeId'])   
        #QualificationType Builder: 31GBYMVNTPAFKSBKTSIEO5PPC5JEYS     

elif create_hit:
     hit = mturk.create_hit(
            Reward='0.00',
            LifetimeInSeconds=3600,
            AssignmentDurationInSeconds=600,
            MaxAssignments=1,
            Title='Play collaborative Minecraft game!',
            Description='A test HIT that requires a certain score from a qualification test to accept.',
            Keywords='boto, qualification, test, minecraft,',
            Question = input,
            AutoApprovalDelayInSeconds=0,
            #QualificationRequirements=[{'QualificationTypeId':'3VVYNZTOM4F04PKWZBNQCCFZCZVADD',
            #                           'Comparator': 'EqualTo',
            #                           'IntegerValues':[100]}]
        ) 
     print('HIT Id ' + hit['HIT']['HITId'])
    #Add here update of the database

elif get_results:
     results = pd.DataFrame()
     all_hits = mturk.list_hits()['HITs']
     hit_ids = [item['HITId'] for item in all_hits]
        # Get the status of all the HITs
     for hit_id in hit_ids:
            result_item = []
            hit_status = mturk.get_hit(HITId=hit_id)["HIT"]["HITStatus"]
            # Get a list of the Assignments that have been submitted
            worker_results = mturk.list_assignments_for_hit(
                HITId=hit_id,
                AssignmentStatuses=['Submitted', 'Approved']
            )
            print(worker_results["NumResults"])
            if worker_results["NumResults"] > 0:
                new_row = {"HITId": hit_id}
                assignments = worker_results['Assignments']
                answers = []
                for assignment in assignments:
                    # Retreive the attributes for each Assignment
                    new_row['WorkerId'] = assignment['WorkerId']
                    assignment_id = assignment['AssignmentId']
                    xml_doc = xmltodict.parse(assignment["Answer"])
                    print("Worker's answer was:")
                    # Parse the XML response
                    if type(xml_doc["QuestionFormAnswers"]["Answer"]) is list:
                        # Multiple fields in HIT layout
                        for answer_field in xml_doc["QuestionFormAnswers"]["Answer"]:
                            input_field = answer_field["QuestionIdentifier"]
                            answer = answer_field["FreeText"]
                            print("LIST For input field: " + input_field)
                            print("LIST Submitted answer: " + str(answer))
                            new_row["Answer.{}".format(input_field)] = answer
                        results = results.append(new_row, ignore_index=True)
                    else:
                        # One field found in HIT layout
                        answer = xml_doc["QuestionFormAnswers"]["Answer"]["FreeText"]
                        input_field = xml_doc["QuestionFormAnswers"]["Answer"]["QuestionIdentifier"]
                        print("For input field: " + input_field)
                        print("Submitted answer: " + answer)
                        new_row["Answer.{}".format(input_field)] = answer
                        results = results.append(new_row, ignore_index=True)
                    
                    # Approve the Assignment (if it hasn't been already)
                    if assignment['AssignmentStatus'] == 'Submitted':
                        mturk.approve_assignment(
                            AssignmentId=assignment_id,
                            OverrideRejection=False
                        )
            #mturk.delete_hit(HITId=hit_id)                                 
     results.to_csv("turk_output.csv", index=False)

if test_ids:
    with open(os.path.join(dirname,'target-structures/list_game_ids.txt')) as f:
        content = f.readlines()
        print(content)
    content = [x.strip() for x in content]      


def create_screenshot_path_till_view(game_id, step_id):
    if step_id-1 < 0:
        # XXX make into an error
        print('Something went wrong: cannot create create_screenshot_path [step_id -1 < 0]')
    else:
        print("The path to builder intermidiate world is [/builder-data/{}/step-{}]".format(game_id,step_id-1))    
        return "/builder-data/{}/step-{}".format(game_id,step_id-1)   









 




