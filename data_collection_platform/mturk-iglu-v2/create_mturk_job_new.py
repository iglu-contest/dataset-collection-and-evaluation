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
import random 

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
from datetime import datetime, timedelta

from langdetect import detect


def initialize_job(env):
    global connect_str_key, sas, mturk, dirname #mr_Role
    connect_str_key = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    sas = os.getenv("AZURE_SAS")
    access_key = os.getenv("AWS_ACCESS_KEY_ID_LIT")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY_LIT")
    dirname = os.path.dirname(__file__)
    # mr_Role = "reduced"

    env_var = env

    if env_var == 'prod':
        create_hits_in_production = True
    elif env_var == 'sandbox':
        create_hits_in_production = False

    print("Initializing in {} environment".format(env_var))

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

    print("Available balance in account: {}".format(mturk.get_account_balance()['AvailableBalance']))

    


def create_qualification_test(type_hit:str):
    qual_response = mturk.create_qualification_type(
                    Name='Test to qualify for fun collaborative Minecraft Game',
                    Keywords='test, qualification, sample, minecraft, iglu',
                    Description='This is a brief description of the game\'s rules with examples of what the builder HIT will look like. It also includes a consent form that should be approved, otherwise we cannot collect data from you.',
                    QualificationTypeStatus='Active',
                    Test=open(os.path.join(dirname,'input/reduced-merged-qualification-questions.xml'), 'r').read(),
                    AnswerKey=open(os.path.join(dirname,'input/reduced-merged-qualification-answers.xml'), 'r').read(),
                    RetryDelayInSeconds=300,
                    TestDurationInSeconds=600) 
    print('QualificationType merged has been created with the following ids: '+ qual_response['QualificationType']['QualificationTypeId'])               


def create_hit_given_type_template (type_hit:str, template_hit:str):
    common_kwargs = dict(
         LifetimeInSeconds=604800,
         MaxAssignments=1,
         Keywords='boto, qualification, iglu, minecraft,',
         AutoApprovalDelayInSeconds=3600,
    )

    # qualification_test('reduced') # in sandbox 3EJZW0TH3GUNEXVCXI1CABUNPVZ96E, in prod 3SR1M7GDJ3VD1FMG2M7X345A544A2K
    
    if env_var == 'prod':
        qualification_type_id = '3SR1M7GDJ3VD1FMG2M7X345A544A2K'
    else:
        qualification_type_id = '3EJZW0TH3GUNEXVCXI1CABUNPVZ96E'

   
    hit = mturk.create_hit(
            **common_kwargs,
            Reward='0.60',
            AssignmentDurationInSeconds=480,
            Title='IGLU - Play collaborative Minecraft game!',
            Description='Perform an action in a Minecraft like world and describe the action in the form of an instruction. ',
            Question = template_hit,
            QualificationRequirements=[{'QualificationTypeId': qualification_type_id, 
                                        'Comparator': 'GreaterThan',
                                        'IntegerValues':[80]
                                        }
                                        # ,{'QualificationTypeId': '00000000000000000071',
                                        # 'Comparator': 'In',
                                        # 'LocaleValues': [{ 'Country': "US" },{ 'Country': "IN" }]
                                        # }
                                    ]
        ) 
    print('HIT created with Id {} for type {}'.format(hit['HIT']['HITId'], type_hit))
    return hit['HIT']['HITId']
     

def is_English(input):
    if input is not None:
        if bool(re.match('^(?=.*[a-zA-Z])', input)):
            if detect(input) == 'en':
                print("Text is in {}".format(detect(input)))
                return True
            else:
                return False
        else:
            return False
    else:
        return False                   
    

def approve_processed_assignment(processed_hits):
     # Approve the Assignment (if it hasn't been already)
    for hit_id in processed_hits:
        worker_results = mturk.list_assignments_for_hit(
                HITId=hit_id,
                AssignmentStatuses=['Submitted']
            )
        if worker_results["NumResults"] > 0:
            assignments = worker_results['Assignments']
            for assignment in assignments:
                    assignment_id = assignment['AssignmentId']
                    print("Approving Assignment id: {}, Hit id: {}".format(assignment_id, hit_id))
                    if assignment['AssignmentStatus'] == 'Submitted':
                        mturk.approve_assignment(
                        AssignmentId=assignment_id,
                        OverrideRejection=False
                        )
                        
                        # mturk.delete_hit(HITId=hit_id)


def get_complete_assignments():
    results = {}
    all_hits = mturk.list_hits()['HITs']
    hit_ids = [item['HITId'] for item in all_hits]
    for hit_id in hit_ids:
            #hit_status = mturk.get_hit(HITId=hit_id)["HIT"]["HITStatus"]
            # Get a list of the Assignments that have been submitted
            worker_results = mturk.list_assignments_for_hit(
                HITId=hit_id,
                AssignmentStatuses=['Submitted']
            )
            #print(worker_results["NumResults"])
            if worker_results["NumResults"] > 0:
                # print("Submitted hit: ",hit_id)
                assignments = worker_results['Assignments']
                for assignment in assignments:
                    new_row = {}
                    # Retreive the attributes for each Assignment
                    new_row['WorkerId'] = assignment['WorkerId']
                    xml_doc = xmltodict.parse(assignment["Answer"])
                    #Parse the XML response
                    if type(xml_doc["QuestionFormAnswers"]["Answer"]) is list:
                        # Multiple fields in HIT layout
                        for answer_field in xml_doc["QuestionFormAnswers"]["Answer"]:
                            input_field = answer_field["QuestionIdentifier"]
                            answer = answer_field["FreeText"]
                            new_row["{}".format(input_field)] = answer
                        qualified = verify_new_assignment(new_row)
                        new_row['IsHITQualified'] = qualified
                        results[hit_id] = new_row
                    else:
                        # One field found in HIT layout
                        answer = xml_doc["QuestionFormAnswers"]["Answer"]["FreeText"]
                        input_field = xml_doc["QuestionFormAnswers"]["Answer"]["QuestionIdentifier"]
                        new_row["{}".format(input_field)] = answer
                        qualified = verify_new_assignment(new_row)
                        new_row['IsHITQualified'] = qualified
                        results[hit_id] = new_row
                    approve_processed_assignment([hit_id])            
    return results


#EXAMPLES OF ROWs PER TYPE
#architect-normal {'WorkerId': 'A3MA56ZT52HDGA', 'views': 'south', 'instruction': 'place red block next to the blue one', 'IsBuiltStructureComplete': 'yes'}
#architect-cq {'WorkerId': 'A3MA56ZT52HDGA', 'IsClarifyingQuestionClear': 'yes', 'Answer4ClarifyingQuestion': 'yes, you are right put it next to that', 'IsBuiltStructureComplete': 'yes'}
#builder-normal {'WorkerId': 'A3MA56ZT52HDGA', 'IsInstructionClear': 'Yes', 'ClarifyingQuestion': 'hello'}
#builder-cq {'WorkerId': 'A3MA56ZT52HDGA', 'IsInstructionClear': 'Yes'}


def verify_new_assignment(new_row):
    print("Verifying assignment")
    qualified = False
    worker_id = new_row['WorkerId']
    #check if normal architecht is correct:
    #architect-normal {'WorkerId': 'A3MA56ZT52HDGA', 'views': 'south', 'instruction': 'place red block next to the blue one', 'IsBuiltStructureComplete': 'yes'}
    if 'InputInstruction' in new_row.keys():
        instruction = new_row['InputInstruction']

        if instruction is None:
            qualified = False
        
        else:
            is_instruction_english = is_English(instruction)

            if len(instruction.strip()) == 0 or is_instruction_english == False:
                send_message_worker(worker_id, instruction, 'textInput')
            else:
                qualified = True

    return qualified
   
def send_message_worker(worker_id, what_was_wrong, type):
    if type in 'textInput':
        mturk.notify_workers( 
                    Subject='The problem HIT: \'Play collaborative Minecraft game\'',
                    MessageText='Your {} [{}] did not satisfy the suggested requirements. We will still pay you for this hit as we believe it might be a misunderstanding. However, if we notice more mistakes, we would need, unfortunately, to disqualify you from our task.'
                                .format(type, what_was_wrong),
                    WorkerIds=[
                            worker_id,
                    ]
                )
    elif type in 'clear':
        mturk.notify_workers( 
                    Subject='The problem HIT: \'Play collaborative Minecraft game\'',
                    MessageText='You did not specify if {} was clear. We will still pay you for this hit as we believe it might be a misunderstanding. However, if we notice more mistakes, we would need, unfortunately, to disqualify you from our task.'
                                .format(what_was_wrong),
                    WorkerIds=[
                            worker_id,
                    ]
                )                  
    elif type in 'views':
        mturk.notify_workers( 
                    Subject='The problem HIT: \'Play collaborative Minecraft game\'',
                    MessageText='You did not pick the {} from drop down list. We will still pay you for this hit as we believe it might be a misunderstanding. However, if we notice more mistakes, we would need, unfortunately, to disqualify you from our task.'
                                .format(what_was_wrong),
                    WorkerIds=[
                            worker_id,
                    ]
                )         


def create_template_given_type (type_hit, **kwargs):
    escaped_kwargs = {}
    for key, value in kwargs.items():
        #silly check if it's sas to avoid html escape
        if key == 'sas':
           escaped_kwargs[key] = str(value) 
           print('Sas is {}'.format(value))
        else:
           escaped_kwargs[key] = html.escape(str(value))    
    return Template(open(os.path.join(dirname,'input/{}.xml'.format(type_hit)), 'r').read()).substitute(**escaped_kwargs)


def print_dict (results):
    for key in results:
        print('Key is {}'.format(key)) 
        print('Value is {}'.format(results[key]))                                          


#EXAMPLES OF ROWs PER TYPE
#architect-normal {'WorkerId': 'A3MA56ZT52HDGA', 'views': 'south', 'instruction': 'place red block next to the blue one', 'IsBuiltStructureComplete': 'yes'}
#architect-cq {'WorkerId': 'A3MA56ZT52HDGA', 'IsClarifyingQuestionClear': 'yes', 'Answer4ClarifyingQuestion': 'yes, you are right put it next to that', 'IsBuiltStructureComplete': 'yes'}
#builder-normal {'WorkerId': 'A3MA56ZT52HDGA', 'IsInstructionClear': 'Yes', 'ClarifyingQuestion': 'hello'}
#builder-cq {'WorkerId': 'A3MA56ZT52HDGA', 'IsInstructionClear': 'Yes'}

def create_turk_job(env, games_count = 30):
       
    if env == 'prod':
        table_hits = "HitsTableSingleTurn"
    elif env == 'sandbox':
        table_hits = "TestHitsTableSingleTurn"

    initialize_job(env)
    create_tables_if_not_exist(table_hits)

    with TableClient.from_connection_string(conn_str=connect_str_key, table_name=table_hits) as table_client_hits:
        
        init_hits(games_count, table_client_hits)

        results = {}
        while 1:
            results = get_complete_assignments()
            print('Inside create turk job: retrieved results')
            if results:
                print('Results dict:')
                print(results)
                processed_hits = []
                for RowKey in results:
                    processed_hits.append(RowKey)
                    game_hit_result = results[RowKey]
                    entity_dict = {}

                    #retrieving row for Hit which exists in the Hits table
                    try:
                        print('Hit id or Row Key to query Hits table is {}'.format(RowKey))
                        # merge_entity = table_client_hits.get_entity(row_key=RowKey)
                        entity = table_client_hits.query_entities(query_filter="RowKey eq '" + RowKey + "'")
                    except ResourceExistsError: 
                        print('HIT {} is not present in Hits table'.format(RowKey)) 

                    for row in entity:
                        for key in row:
                            entity_dict[key] = row[key]

                    # merging entity dict with updated values after processing Hit
                    for answer in game_hit_result:
                        entity_dict[answer] = game_hit_result[answer]

                    for item in entity_dict:
                        print('Mehtod: create_mturk_job(): Entity to be merged: Key is {} and value is {}'.format(item, entity_dict[item]))

                    table_client_hits.upsert_entity(mode=UpdateMode.MERGE, entity=entity_dict)
                    print("Updated above row entity in Hits Table")

                print("Processed hits: ", processed_hits)  
            else:
                print('Waiting on results for hits results...')
                t.sleep(60)
   

def rename_builder_files(game_id, step_id):
    if env_var == 'prod':
        subpath = 'builder-data/{}/'.format(game_id)
    else:
        subpath = 'test-builder-data/{}/'.format(game_id)

    file2move = []
    file2move.append('step-{}'.format(step_id))
    file2move.append('step-{}_east.png'.format(step_id))
    file2move.append('step-{}_west.png'.format(step_id))
    file2move.append('step-{}_south.png'.format(step_id))
    file2move.append('step-{}_north.png'.format(step_id))
    file2move.append('step-{}_top.png'.format(step_id))
    for item in file2move:
        rename_blob_files('{}{}'.format(subpath,item),'{}disqualified_{}'.format(subpath,item))


def rename_blob_files(source_file_path, target_file_path):
    # Source
    source_container_name = "mturk-vw"
    blob_service_client = BlobServiceClient.from_connection_string(connect_str_key)
    source_blob = (f"https://iglumturkstorage.blob.core.windows.net/{source_container_name}/{source_file_path}")

    # Target
    target_container_name = "mturk-vw"
    copied_blob = blob_service_client.get_blob_client(target_container_name, target_file_path)
    copied_blob.start_copy_from_url(source_blob)
    print('Method: rename_blob_files Source is {} and Target is {}'.format(source_blob, copied_blob))

    # Delete source
    remove_blob = blob_service_client.get_blob_client(source_container_name, source_file_path)
    remove_blob.delete_blob()


def create_new_hit(max_num_steps_game, games, table_client_games, table_client_hits, attempt_id, structure_id, game_info, game_id, merged_entity, current_step_id):
    if env_var == 'prod':
        builder_data_path = 'builder-data'
    else:
        builder_data_path = 'test-builder-data'

    create_builder_normal(table_client_hits, 
                        attempt_id, 
                        structure_id, 
                        game_id, 
                        merged_entity, 
                        current_step_id,
                        builder_data_path)
 


def create_builder_normal(table_client_hits, game_id, initial_world):
    template = ''
    new_hit_type = "builder-normal"
    builder_data_path_in_blob = initial_world.split('/')[0]
    screenshot_game_id_in_blob = initial_world.split('/')[1]
    screenshot_step_view_in_blob = initial_world.split('/')[2][:-4]
    screenshot_step_in_blob = screenshot_step_view_in_blob.split('_')[0]


    # print("{}  {} {} {}".format(builder_data_path_in_blob, screenshot_game_id_in_blob, screenshot_step_view_in_blob, screenshot_step_in_blob))

    print('Rendering builder-normal template')
    template = create_template_given_type(
                                    new_hit_type,
                                    gameId=game_id,
                                    builderDataPath=builder_data_path_in_blob,
                                    screenshotGameId=screenshot_game_id_in_blob,
                                    screenshotStepView=screenshot_step_view_in_blob,
                                    screenshotStep = screenshot_step_in_blob,
                                    sas=sas
                                    )

    new_hit_id = create_hit_given_type_template(new_hit_type, template)

    # hit_input['InitialWorld'] = initial_world

    create_new_row4new_hit(table_client_hits,
                            game_id, 
                            new_hit_id,
                            new_hit_type,
                            initial_world) 

    print('Done creating builder-normal')
    return new_hit_id 

def create_new_row4new_hit(table_client_hits, game_id, new_hit_id, hit_type, initial_world):
    entity_to_insert = {}
    hit_input = {}
    #entity to be inserted for new hit
    entity = {
            "PartitionKey": str(game_id),
            "RowKey": new_hit_id,
            "HitType": hit_type,
            "IsHITQualified" : "NA",
            "WorkerId" : "NA",
            "InitializedWorld" : initial_world,
            "InputInstruction" : "NA",
            "InstructionToExecute": "NA",
            "IsInstructionClear" : "NA",
            "ClarifyingQuestion" : "NA"
            }

    if  len(hit_input) == 0:
        entity_to_insert = entity   
    else: 
        entity_to_insert = merge_dicts(entity, hit_input)     
    print('New Hit row to insert is: {}'.format(entity_to_insert)) 
    try:        
        table_client_hits.create_entity(entity_to_insert)
        print('Successfully inserted new entity into table ')
    except ResourceExistsError:
        print("Entity {hitId} already exists!".format(hitId=new_hit_id))

def merge_dicts(x, y):
    # print("x is {} and y is {}".format(x, y))
    if len(y) > 0: 
       z = x.copy() # start with x's keys and values
       z.update(y) # modify z with y's keys and values
       return z
    else:
        return x   


def init_hits(games_count, table_client_hits):

    if games_count <= 0:
        print("Not creating any Hits as games count is less than 1")

    else:

        if env_var == 'prod':
            builder_data_path = 'builder-data'
        else:
            builder_data_path = 'test-builder-data'
        
        source_container_name = "mturk-vw" 

        container_client = ContainerClient.from_connection_string(connect_str_key, source_container_name)
        blob_names = container_client.list_blobs(name_starts_with= builder_data_path)
        blob_list = []

        game_id = game_id_to_initialize(table_client_hits) + 1

        #initializing intermediate worlds for workers to perform actions in
        for blob in blob_names:
            if ".png" in blob.name: #check to ensure initialized world is from image
                blob_list.append(blob.name)

        random_selected_worlds = random.sample(blob_list, games_count)

        for initial_world in random_selected_worlds:
            create_builder_normal(table_client_hits, game_id, initial_world)
            game_id = game_id + 1
       

def game_id_to_initialize(table_client_hits):
 
    max_game_id = 0
    datetime_now = datetime.today()
    datetime_now_z = datetime_now.strftime("%Y-%m-%dT%H:%M:%S%zZ")

    query_filter = "Timestamp le datetime'{datetimeNow}'".format(datetimeNow = datetime_now_z)
    entities = list(table_client_hits.query_entities(
        query_filter=query_filter,
        select=['PartitionKey','RowKey','Timestamp']))

    if len(entities) < 1:
        return max_game_id
    else:
        for row in entities:
            cur_id = int(row['PartitionKey'])
            if cur_id > max_game_id:
                max_game_id = int(row['PartitionKey'])

    return max_game_id

def create_tables_if_not_exist(table_hits):
    print("Creating table for hits is [{}]".format(table_hits))
    with TableServiceClient.from_connection_string(connect_str_key) as table_service_client:
             table_service_client.create_table_if_not_exists(table_name = table_hits)
             print("Table for hits is {} is successfully created".format(table_hits))
       

if __name__ == "__main__":
 ## Creating qualification tests -- need to do it only once, main purpose is to display consent form 
    # create_qualification_test('architect')
    # create_qualification_test('builder')
    # create_qualification_test('merged') #current id is 3FIQMFNPAF983ZZ6YSKHSCP7UKFN6Q
    # create_qualification_test('reduced') # in sandbox 3EJZW0TH3GUNEXVCXI1CABUNPVZ96E, in prod 3SR1M7GDJ3VD1FMG2M7X345A544A2K

    parser = argparse.ArgumentParser()
  
    parser.add_argument(
       "--env",
    #    description="Accepted arguments are prod or sandbox",
       type=str,
       required=True
    )

    parser.add_argument(
       "--games_count",
    #    description="Number of games to be initialized",
       type=str,
       required=True
    )

    args = parser.parse_args()
    env_var = args.env
    games_count = int(args.games_count)
            
   
    create_turk_job(env_var, games_count)