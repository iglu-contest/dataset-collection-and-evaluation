import html
from re import template
import xmltodict
import boto3
import json
import pandas as pd
import os
import argparse
import re
from urllib.parse import quote
from string import Template
import sys 

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, __version__
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError
from azure.data.tables import TableClient
from azure.data.tables import UpdateMode
from azure.core.exceptions import HttpResponseError

import os, uuid
import time as t
from datetime import datetime

from langdetect import detect

create_hits_in_production = False

connect_str_key = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
sas = os.getenv("AZURE_SAS")
access_key = os.getenv("AWS_ACCESS_KEY_ID_LIT")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY_LIT")
dirname = os.path.dirname(__file__)
a_Role = "architect"
b_Role = "builder"

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

def delete_hits_by_id(path2list_hist:str):
    hits = list_structure_ids(path2list_hist)
    for item in hits:
        response = mturk.delete_hit(
            HITId=item
        )

def list_structure_ids(file_name:str):
    with open(os.path.join(dirname, file_name)) as f:
        content = f.readlines()
        content = [x.strip() for x in content] 
    return content

def delete_hits():
    # Check if there are outstanding assignable or reviewable HITs
    all_hits = mturk.list_hits()["HITs"]
    hit_ids = [item["HITId"] for item in all_hits]
    # This is slow but there's no better way to get the status of pending HITs
    for hit_id in hit_ids:
        # Get HIT status
        mturk.delete_hit(HITId=hit_id)

def delete_assignable_hit():
   for item in mturk.list_hits()['HITs']:
        hit_id=item['HITId']
        print('HITId:', hit_id)
        status=mturk.get_hit(HITId=hit_id)['HIT']['HITStatus']
        print('HITStatus:', status)
    # If HIT is active then set it to expire immediately
        if status=='Assignable':
            mturk.update_expiration_for_hit(
                HITId=hit_id,
                ExpireAt=datetime(2015, 1, 1)
            )  
    # Delete the HIT
        try:
            mturk.delete_hit(HITId=hit_id)
        except:
            print('Not deleted')
        else:
            print('Deleted {}'.format(hit_id))

def get_hit_list_status():
    # Check if there are outstanding assignable or reviewable HITs
    all_hits = mturk.list_hits()["HITs"]
    hit_ids = [item["HITId"] for item in all_hits]
    hit_status = {
        "assignable": [],
        "reviewable": [],
        "unassignable" : []
    }
    # This is slow but there's no better way to get the status of pending HITs
    for hit_id in hit_ids:
        # Get HIT status
        status = mturk.get_hit(HITId=hit_id)["HIT"]["HITStatus"]
        #creationTime = mturk.get_hit(HITId=hit_id)["HIT"]["CreationTime"]
        NumberOfAssignmentsPending = mturk.get_hit(HITId=hit_id)["HIT"]["NumberOfAssignmentsPending"]
        if status == "Assignable":
            hit_status["assignable"].append((hit_id, NumberOfAssignmentsPending))
        elif status == "Reviewable":
            hit_status["reviewable"].append((hit_id, NumberOfAssignmentsPending))
        elif status == "Unassignable":
            hit_status["unassignable"].append((hit_id, NumberOfAssignmentsPending))
    print("HITStatus: {}".format(hit_status))


    #print(mturk.get_hit(HITId="3QX22DUVPXLUEJ7ZWNZU2PCLX9LMV0"))
    return hit_status


def send_message_to_list_of_workers(workers, msg):
    for worker_id in workers:
        if msg == 'structureIncomplete':
            mturk.notify_workers( 
                            Subject='The problem \'Play collaborative Minecraft game\'',
                            MessageText="""It looks like you have misunderstood the point of the question 
                                        "If the structure is complete?" You need to pick yes only if initial 
                                        structure is exactly the same as target which is not the case for 
                                        all the cases where you have indicated the completness. We will still 
                                        pay you for this hit as we believe it might be a misunderstanding. 
                                        However, if we notice more mistakes, we would unfortunately need to 
                                        disqualify you from our task.""",
                            WorkerIds=[
                                    worker_id,
                            ]
                        )  
        if msg == 'qualificationTypeError':
            mturk.notify_workers( 
                            Subject='The problem \'Play collaborative Minecraft game\'',
                            MessageText="""It looks like there was an issue with the play collaborative Minecraft task which was preventing you from doing the task.
                            The issue is now fixed.
                            The following tasks should be available to you without the need for qualification:
                            "Play collaborative Minecraft game as an architect for pre-approved gamer!",
                            "Play collaborative Minecraft game as a builder for pre-approved gamer!"
                            Let us know if you are still facing any issues. Our e-mail is MSR_LIT@outlook.com.
                            Thank you!""",
                            WorkerIds=[
                                    worker_id,
                            ]
                        )  
            print("Message sent to ",worker_id)

def get_qualification_types():
    qualifications= mturk.list_qualification_types(
        Query='iglu',
        MustBeRequestable=False,
        MustBeOwnedByCaller=True)

    for qualId in qualifications['QualificationTypes']:
        # print(qualId['QualificationTypeId'])
        print(qualId['QualificationTypeId'], qualId['QualificationTypeStatus'], qualId['Name'])
    
def delete_qualification_types(input:str):
    qualifications = mturk.list_qualification_types(
        Query = input,
        MustBeRequestable=False,
        MustBeOwnedByCaller=True)

    for qualId in qualifications['QualificationTypes']:
        # print(qualId['QualificationTypeId'])
        cur_qual_id = qualId['QualificationTypeId']
        print("Deleting Qualification Id: ", cur_qual_id)
        mturk.delete_qualification_type(QualificationTypeId= cur_qual_id)

def get_compete_assignments():
    results = {}
    all_hits = mturk.list_hits()['HITs']
    hit_ids = [item['HITId'] for item in all_hits]
    for hit_id in hit_ids:
            print('HITID is {}'.format(hit_id))
            #hit_status = mturk.get_hit(HITId=hit_id)["HIT"]["HITStatus"]
            # Get a list of the Assignments that have been submitted
            worker_results = mturk.list_assignments_for_hit(
                HITId=hit_id,
                AssignmentStatuses=['Submitted', 'Approved']
            )
            #print(worker_results["NumResults"])
            if worker_results["NumResults"] > 0:
                assignments = worker_results['Assignments']
                answers = []
                for assignment in assignments:
                    new_row = {}
                    # Retreive the attributes for each Assignment
                    new_row['WorkerId'] = assignment['WorkerId']
                    assignment_id = assignment['AssignmentId']
                    xml_doc = xmltodict.parse(assignment["Answer"])
                    #Parse the XML response
                    if type(xml_doc["QuestionFormAnswers"]["Answer"]) is list:
                        # Multiple fields in HIT layout
                        for answer_field in xml_doc["QuestionFormAnswers"]["Answer"]:
                            input_field = answer_field["QuestionIdentifier"]
                            answer = answer_field["FreeText"]
                            new_row["{}".format(input_field)] = answer
                        results[hit_id] = new_row  
                    
                    else:
                        # One field found in HIT layout
                        answer = xml_doc["QuestionFormAnswers"]["Answer"]["FreeText"]
                        input_field = xml_doc["QuestionFormAnswers"]["Answer"]["QuestionIdentifier"]
                        new_row["{}".format(input_field)] = answer
                        results[hit_id] = new_row  

                    # Approve the Assignment (if it hasn't been already)
                    if assignment['AssignmentStatus'] == 'Submitted':
                        mturk.approve_assignment(
                        AssignmentId=assignment_id,
                        OverrideRejection=False
                        )
                        mturk.delete_hit(HITId=hit_id)
    print_dict(results)   
    print('Done with the getting the assignments')             
    return results  

def print_dict (results):
    for key in results:
        print('Key is {}'.format(key)) 
        print('Value is {}'.format(results[key]))      

def create_block (workers):
    #workers=['AONSG5WOC3OX0']
    for worker_id in workers:
        response = mturk.create_worker_block(
                    WorkerId=worker_id,
                    Reason='The worker is not following the intructions properly by indicating that the structure is complete -- when it\'s actually not'
        )
        print("Blocked worker id : {}".format(worker_id))


def update_qualification(id:str):
    print("Updating qualification {} to 2 min".format(id))
    mturk.update_qualification_type(
        QualificationTypeId=id,
        Description='This is a brief description of the game\'s rules with examples of what the builder HIT will look like. It also includes a consent form that should be approved, otherwise we cannot collect data from you.',
        QualificationTypeStatus='Active',
        Test=open(os.path.join(dirname,'input/reduced-merged-qualification-questions.xml'), 'r').read(),
        AnswerKey=open(os.path.join(dirname,'input/reduced-merged-qualification-answers.xml'), 'r').read(),
        TestDurationInSeconds=600,
        RetryDelayInSeconds=300,
    )        

def qualify_allow_list_workers(allow_list_workers_HitId):
    for worker in allow_list_workers_HitId:
        mturk.associate_qualification_with_worker(
            QualificationTypeId='32IU3MUE9M649TMT5TLMP0CD6O86EW',
            WorkerId=worker,
            IntegerValue=111,
            SendNotification=True)

def send_bonus_to_wokers(allow_list_workers_HitId): 
    msg = ''' Dear worker! 
    Thank you so much for participating in our study: "Play collaborative Minecraft game as an architect/builder!" 
    You did an excellent job -- so we have decided to reward you with bonus! We are writing to you in order to invite to work on the following HITS: 
    "Play collaborative Minecraft game as an architect for pre-approved gamer!"
    "Play collaborative Minecraft game as a builder for pre-approved gamer!"
    These tasks will be feasible only to limited amount of people who did great as well. They will also have increased reward! 
    We would really appreciate if you can find time to work on those HITS in the coming 2-3 days. 
    Please let us know if you have any questions! We will initiate more studies coming month! Thanks, IGLU team'''

    for worker in allow_list_workers_HitId:
        assignment = mturk.list_assignments_for_hit(
            HITId=allow_list_workers_HitId[worker]
        ) 

        assignmentId = assignment['Assignments'][0]['AssignmentId']

        mturk.send_bonus(
            WorkerId=worker,
            BonusAmount='5',
            AssignmentId=assignmentId,
            Reason=msg)

def list_all_bonus_payments(allow_list_workers_HitId):

    for worker in allow_list_workers_HitId:
        print(
            mturk.list_bonus_payments(
            HITId=allow_list_workers_HitId[worker]
            )
        )

if __name__ == "__main__":
    # delete_hits_by_id('list_hits_to_delete.txt')   
    # delete_hits()
    # delete_assignable_hit()
  
    allow_list_workers_HitId={'A132MSWBBVTOES': '3QTFNPMJDFMH5LX99L3X0AEHPAJNZI',
    'A1JTIHM006U9WM': '3Y40HMYLMAM5VGH354RYHKQ0QVHUX2',
    'A1P3HHEXWNLJMP': '3RTFSSG7UHANNQPJML3BOEGA470WL9',
    'A1SX8IVV82M0LW': '3OJX0UFJ18BFUKZ52OLK1H4IHYWU9Z',
    'A1VMPZVVVZUCS4': '3X52SWXE169UKMVD98ACLVQN8ZWCWJ',
    'A2173NB4RXYT6M': '3QE4DGPGC0FVSWSY1O0CGUSBMY44GE',
    'A21K7FBCJ54ILS': '3UZUVSO3QGZDC8LD1XAK2LOZV9AMEA',
    'A2F1AA15HG0FRU': '39KV3A5D2HBV1OJ8YMS08KVO35I7S5',
    'A2ZGZQDUKF2B4G': '3XU80RHWI8KFGGZE6NYB75V8YNO44A',
    'A34359DSZPY7LR': '3OZ4VAIBF6J4DB1ETQM2MXK4TV5VJG',
    'A34XI67018IK8': '30Z7M1Q8V7OV162XRRYF1KXDRUF8AG',
    'A3APKUC67F9IMW': '3W1K7D6QTKLF4C8C6VYO9FEN9A8BZZ',
    'A3FUTMLIR91OLE': '3NBFJK3IPQMZWP2GK8FLUSYG5ATGOX',
    'A80XRGJXN2D22': '3WGZLY9VDQQTZD59B1PHRL5JDDH8DK',
    'AEIACTPDXL4MJ': '3OND0WXMI5JRKUK2A0U7AGG3GMNEH5',
    'AFIK3VBMMX6G6': '3LOJFQ4BP6JDUE7AKQMKHQEA6S0KDW',
    'AKXG6X1KVMNZ0': '3HEM8MA6IIG8UE8V24XCD678LB2QP5',
    'AONSG5WOC3OX0': '3WGZLY9VDQQTZD59B1PHRL5JBS7D87',
    'AOWW3URQNRJ6U': '3TC2K6WKAP66W37TEC50V2EFGVP28K',
    'AYU6628HU3FUP': '3GL25Y685CYMI8CUW20CQA96BF6XMF'}
    # list_all_bonus_payments(allow_list_workers_HitId)
    # qualify_allow_list_workers(allow_list_workers_HitId)
    # send_bonus_to_wokers(allow_list_workers_HitId)
    # delete_assignable_hit()

    get_hit_list_status()
    #get_qualification_types()
    #get_compete_assignments()
    #delete_qualification_types("Minecraft Game")
    # workers=['A1VBAI9GBDQSMO']
    # send_message_to_list_of_workers(allow_list_workers_HitId, 'qualificationTypeError')
    # create_block(workers)
    # list_q_tests()
    #retrieve_answers()
    # update_qualification('3SR1M7GDJ3VD1FMG2M7X345A544A2K')
