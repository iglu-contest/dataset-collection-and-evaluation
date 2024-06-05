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
from datetime import datetime, timedelta

from langdetect import detect


connect_str_key = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
sas = os.getenv("AZURE_SAS")
access_key = os.getenv("AWS_ACCESS_KEY_ID_LIT")
secret_key = os.getenv("AWS_SECRET_ACCESS_KEY_LIT")
dirname = os.path.dirname(__file__)
a_Role = "architect"
b_Role = "builder"
m_Role = "merged"
mr_Role = "reduced"


#create_qualification_test_a = False #Tested: QT for Architect has been created, id below
#create_qualification_test_b = False #Tested: QT for Builder has been created, id below
env_var = sys.argv[1]

if env_var == 'prod':
    create_hits_in_production = True
elif env_var == 'sandbox':
    create_hits_in_production = False

### DEFAULT_VALUES
### END DEFAULT VALUES

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


def list_structure_ids(path_game_ids:str):
    print("Listing structure ids in file:")
    with open(os.path.join(dirname, path_game_ids)) as f:
        content = f.readlines()
        content = [x.strip().lower() for x in content] 
        print(content)
    if len(content)==0:
        print('Specified input file {} is empty')
    else:     
       return content  


def create_qualification_test(type_hit:str):
    if type_hit == a_Role:
            qual_response = mturk.create_qualification_type(
                            Name='Test',
                            Keywords='test, qualification, sample, minecraft, iglu',
                            Description='This is a Qualification test to perform architect Roles in a collaborative Minecraft game, including a consent form.',
                            QualificationTypeStatus='Active',
                            Test=open(os.path.join(dirname,'input/architect-qualification-questions.xml'), 'r').read(),
                            AnswerKey=open(os.path.join(dirname,'input/architect-qualification-answers.xml'), 'r').read(),
                            RetryDelayInSeconds=300,
                            TestDurationInSeconds=120)
            print('QualificationType architect has been created with the following ids: '+qual_response['QualificationType']['QualificationTypeId'])
            #Test QualificationType architect: 3F97VQZTZ36ANTIH9STV6NGP8XZUHP #test
    elif type_hit == b_Role:
            qual_response = mturk.create_qualification_type(
                            Name='Qualification test to qualify as a Builder in Minecraft Game',
                            Keywords='test, qualification, sample, minecraft, iglu',
                            Description='This is a brief description of the game\'s rules with examples of what the builder HIT will look like. It also includes a consent form.',
                            QualificationTypeStatus='Active',
                            Test=open(os.path.join(dirname,'input/builder-qualification-questions.xml'), 'r').read(),
                            AnswerKey=open(os.path.join(dirname,'input/builder-qualification-answers.xml'), 'r').read(),
                            RetryDelayInSeconds=300,
                            TestDurationInSeconds=300)
            print('QualificationType builder has been created with the following ids: '+ qual_response['QualificationType']['QualificationTypeId'])   
            #Test QualificationType Builder: 31GBYMVNTPAFKSBKTSIEO5PPC5JEYS #test     
    elif type_hit == m_Role:
            qual_response = mturk.create_qualification_type(
                            Name='Test to qualify for collaborative Minecraft Game v1 ',
                            Keywords='test, qualification, sample, minecraft, iglu',
                            Description='This is a brief description of the game\'s rules with examples of what the builder HIT will look like. It also includes a consent form that should be approved, otherwise we cannot collect data from you.',
                            QualificationTypeStatus='Active',
                            Test=open(os.path.join(dirname,'input/merged-qualification-questions.xml'), 'r').read(),
                            AnswerKey=open(os.path.join(dirname,'input/merged-qualification-answers.xml'), 'r').read(),
                            RetryDelayInSeconds=300,
                            TestDurationInSeconds=300) 
            print('QualificationType merged has been created with the following ids: '+ qual_response['QualificationType']['QualificationTypeId'])
    elif type_hit == mr_Role:
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
    else:
        print('Qualification can be only of two types: either architect or builder. No qualification test have been created')


def create_hit_given_type_template (type_hit:str, template_hit:str):
    common_kwargs = dict(
         LifetimeInSeconds=604800,
         MaxAssignments=1,
         Keywords='boto, qualification, test, minecraft,',
         AutoApprovalDelayInSeconds=3600,
    )

    # qualification_test('reduced') # in sandbox 3EJZW0TH3GUNEXVCXI1CABUNPVZ96E, in prod 3SR1M7GDJ3VD1FMG2M7X345A544A2K
    
    if env_var == 'prod':
        qualification_type_id = '3SR1M7GDJ3VD1FMG2M7X345A544A2K'
    else:
        qualification_type_id = '3EJZW0TH3GUNEXVCXI1CABUNPVZ96E'

    if a_Role in type_hit:
        hit = mturk.create_hit(
                **common_kwargs,
                Reward='0.40',
                AssignmentDurationInSeconds=600,
                Title='Play collaborative Minecraft game as an architect!',
                Description='You would be given a target structure, and a structure built so far and asked to give the next instruction for the builder in natural language so that the following steps builder would be able to finish the structure. ',
                Question = template_hit,
                QualificationRequirements=[{'QualificationTypeId': qualification_type_id, 
                                          'Comparator': 'GreaterThan',
                                           'IntegerValues':[80]
                                           },
                                           {'QualificationTypeId': '00000000000000000071',
                                            'Comparator': 'In',
                                            'LocaleValues': [{ 'Country': "US" },{ 'Country': "IN" }]
                                            }
                                        ]
            ) 
        print('HIT Id {} for type {}'.format(hit['HIT']['HITId'], type_hit))
        return hit['HIT']['HITId']
    elif b_Role in type_hit:
         hit = mturk.create_hit(
                **common_kwargs, 
                Reward='0.50',
                AssignmentDurationInSeconds=600,
                Title='Play collaborative Minecraft game as a builder!',
                Description='You would be given instructions in natural language created by others to contribute to building a structure in an interactive voxel world. It is super fun!',
                Question = template_hit,
                QualificationRequirements=[{'QualificationTypeId': qualification_type_id, 
                                           'Comparator': 'GreaterThan',
                                           'IntegerValues':[80]
                                            },
                                            {'QualificationTypeId': '00000000000000000071',
                                            'Comparator': 'In',
                                            'LocaleValues': [{ 'Country': "US" },{ 'Country': "IN" }]
                                            }
                                        ]
            ) 
         print('HIT Id {} for type {}'.format(hit['HIT']['HITId'], type_hit))
         return hit['HIT']['HITId']
    

def is_English(input):
    if input is not None:
        if bool(re.match('^(?=.*[a-zA-Z])', input)):
            if detect(input) == 'en':
                print(detect(input))
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
    #print("All hits are {}".format(all_hits))
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
                print("Submitted hit: ",hit_id)
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
    if 'instruction' in new_row.keys() and 'views' in new_row.keys() and 'IsBuiltStructureComplete' in new_row.keys():
        view = ''
        complete = ''
        view_is_right = False
        complete_is_right = False
        instruction = new_row['instruction']

        is_instruction_english = is_English(instruction)


        if new_row['IsBuiltStructureComplete'] is not None:    
           complete = new_row['IsBuiltStructureComplete'].lower()
        else:
            qualified = False
        print('complete [{}]'.format(complete))
        if complete in ['yes', 'no', 'dontknow']:
            complete_is_right = True
            print('complete [{}] is right'.format(complete))
        else:   
            send_message_worker(worker_id, 'complete', 'complete')

        #when built structure is marked as complete, instruction and view is not necessary to be provided
        if complete != 'yes':
            if new_row['views'] is not None:
                view = new_row['views'].lower()  
            else:
                qualified = False
            print('View is [{}]'.format(view))
            if view in ['north', 'south', 'west', 'east', 'top']:
                view_is_right = True
                print('View [{}] is right'.format(view))
            else:
                send_message_worker(worker_id, 'view', 'views')
            if  is_instruction_english and view_is_right and complete_is_right:
                qualified = True  
            else:
                send_message_worker(worker_id, instruction, 'textInput')  
            print('Intruction is {} and it is english {}'.format(instruction, is_instruction_english))
            print('{} {} {}'.format(is_instruction_english, view_is_right, complete_is_right))
        else:
            qualified = True

    #Check architect-cq 
    #architect-cq {'WorkerId': 'A3MA56ZT52HDGA', 'IsClarifyingQuestionClear': 'yes', 'Answer4ClarifyingQuestion': 'yes, you are right put it next to that', 'IsBuiltStructureComplete': 'yes'}       
    elif 'Answer4ClarifyingQuestion' in new_row.keys() and 'IsClarifyingQuestionClear' in new_row.keys() and 'IsBuiltStructureComplete' in new_row.keys():
            answer = new_row['Answer4ClarifyingQuestion']

            clear =  ''
            if new_row['IsClarifyingQuestionClear'] is not None:
               clear = new_row['IsClarifyingQuestionClear'].lower()  
            else:
                qualified = False

            complete = ''
            if new_row['IsBuiltStructureComplete'] is not None:
               complete = new_row['IsBuiltStructureComplete'].lower() 
            else:
                qualified = False

            complete_is_right = False
            clear_is_right = False
            is_answer_english = is_English(answer)

            if complete in ['yes', 'no', 'dontknow']:
                complete_is_right = True
            else:    
                send_message_worker(worker_id, 'complete', 'complete')

            if clear in ['yes', 'no']:   
               clear_is_right = True
            else:  
                send_message_worker(worker_id, 'clarifying question', 'clear') 
             
            print('{} {} {}'.format(is_answer_english, complete_is_right, clear_is_right))

            if is_answer_english and complete_is_right and clear_is_right:
                 qualified = True
            else:
                send_message_worker(worker_id, answer, 'textInput')   
    #Check builder-normal   
    #builder-normal {'WorkerId': 'A3MA56ZT52HDGA', 'IsInstructionClear': 'Yes', 'ClarifyingQuestion': 'hello'}
    elif 'IsInstructionClear' in new_row.keys() and 'ClarifyingQuestion' in new_row.keys():
            clear = ''
            if new_row['IsInstructionClear'] is not None:
               clear = new_row['IsInstructionClear'].lower()  
            else:
               qualified = False

            question = new_row['ClarifyingQuestion']
            clear_is_right = False
            cq_is_english = is_English(question)

            if clear in ['yes', 'no']:   
               clear_is_right = True
            else:  
                send_message_worker(worker_id, 'instruction', 'clear') 

            if clear == 'yes' and question is None:
                  qualified = True
            elif  clear == 'no' and cq_is_english:
                  qualified = True
            else:
                qualified = False 
                send_message_worker(worker_id, question, 'textInput')   
    #Check builder-cq  
    #builder-cq {'WorkerId': 'A3MA56ZT52HDGA', 'IsInstructionClear': 'Yes'}
    elif 'IsInstructionQAClear' in new_row.keys():
          clear = '' 
          if new_row['IsInstructionQAClear'] is not None:
             clear = new_row['IsInstructionQAClear'].lower() 
          else:
              qualified = False

          if clear in ['yes', 'no']:
             qualified = True
          else:
              qualified = False  
              send_message_worker(worker_id, 'instrution and clarifying quesion with the answer', 'clear') 

    print('qualified {}'.format(qualified))
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
    elif type in 'complete':
         mturk.notify_workers( 
                Subject='The problem HIT: \'Play collaborative Minecraft game as an architect!\'',
                MessageText='You did not pick an answer to identify if the structure is complete from the dropdown list. We will still pay you for this hit as we believe it might be a misunderstanding. However, if we notice more mistakes, we would need, unfortunately, to disqualify you from our task.',
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


def create_game_id(attempt_id, structure_id):
    return '{}-{}'.format(attempt_id,structure_id)

#EXAMPLES OF ROWs PER TYPE
#architect-normal {'WorkerId': 'A3MA56ZT52HDGA', 'views': 'south', 'instruction': 'place red block next to the blue one', 'IsBuiltStructureComplete': 'yes'}
#architect-cq {'WorkerId': 'A3MA56ZT52HDGA', 'IsClarifyingQuestionClear': 'yes', 'Answer4ClarifyingQuestion': 'yes, you are right put it next to that', 'IsBuiltStructureComplete': 'yes'}
#builder-normal {'WorkerId': 'A3MA56ZT52HDGA', 'IsInstructionClear': 'Yes', 'ClarifyingQuestion': 'hello'}
#builder-cq {'WorkerId': 'A3MA56ZT52HDGA', 'IsInstructionClear': 'Yes'}

def create_turk_job(table_hits, table_games, path_target_ids, max_num_steps_game = 30):
    is_it_initial = True
    results = {}
    #game_markComplete_flag = {}
    create_tables_if_not_exist(table_hits, table_games) 
    with TableClient.from_connection_string(conn_str=connect_str_key, table_name=table_games) as table_client_games:
        games = initialize_new_games(path_target_ids, table_games, table_client_games) 
        print('Done with init games')

        for game in list(games):
            print('Initalized game is {}'.format(game))
        
        for attempt_id, structure_id in games:
            game_id= create_game_id(attempt_id, structure_id)

        remaining_active_games = get_remaining_active_games(games, table_client_games)
               
        with TableClient.from_connection_string(conn_str=connect_str_key, table_name=table_hits) as table_client_hits:
            if is_it_initial:
                is_it_initial = False 
                init_hits(games, table_client_hits)
            # for game in list(games):
            #     print('Hit initialized for game: {}'.format(game))

            update_active_games_hit = update_games_latest_hit(remaining_active_games, table_client_hits)
            all_active_games = {**games, **update_active_games_hit}
            
            while all_active_games:
                print("Current unfinished games: ")
                for game in all_active_games:
                    print(game)
                    
                results = get_complete_assignments()
                print('Inside create turk job: retrieved results')
                if results:
                    print('Results dict:')
                    print(results)
                    processed_hits = []
                    for (attempt_id, structure_id), game_info in dict(all_active_games).items():
                        game_id = create_game_id(attempt_id, structure_id) 
                        game_hit_id = game_info["latest_hit"]
                        if game_hit_id not in results.keys():
                            continue
                        else:
                            processed_hits.append(game_hit_id)
                        print("Processed hits: ", processed_hits)
                        game_hit_result = results[game_hit_id]
                        try:
                            print('Partition is {} and row key is {}'.format(game_id,game_hit_id))
                            merged_entity = table_client_hits.get_entity(partition_key=game_id, row_key=game_hit_id)
                        except ResourceExistsError: 
                            print('HIT {} is outside of the scope'.format(game_hit_result))  
                        for answer in game_hit_result:
                                merged_entity[answer] = game_hit_result[answer]
                        
                        if 'IsBuiltStructureComplete' in merged_entity:
                            if merged_entity['IsBuiltStructureComplete'].lower() == 'yes' and merged_entity['IsStructureCompleteFlag'] == 0: 
                            # this flag is set so that more than one worker needs to validate if structure is complete
                                merged_entity['IsStructureCompleteFlag']= 1
                                merged_entity['IsHITQualified']= False
                            elif merged_entity['IsBuiltStructureComplete'].lower() == 'no' and merged_entity['IsStructureCompleteFlag'] == 1:
                                merged_entity['IsStructureCompleteFlag']= 0

                        for item in merged_entity:
                            print('Mehtod: create_mturk_job(): Merged Entity: Key is {} and value is {}'.format(item, merged_entity[item]))

                        table_client_hits.upsert_entity(mode=UpdateMode.MERGE, entity=merged_entity)
                        print("Updated above row entity in Hits Table")

                        if merged_entity['IsHITQualified'] == True:
                        #proceed as valid hit
                            current_step_id = merged_entity["StepId"] + 1  # incrementing step id to go to next step in game
                            create_new_hit(
                            max_num_steps_game, 
                            games, 
                            table_client_games,
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            game_info, 
                            game_id, 
                            merged_entity, 
                            current_step_id)
                        else:
                            current_step_id = merged_entity["StepId"] # no incrementation is happening 
                            #re-crete the same HIT as on previous step
                            re_create_hit(
                                table_client_hits, 
                                attempt_id, 
                                structure_id, 
                                game_info, 
                                game_id, 
                                merged_entity,
                                current_step_id)
                            if current_step_id % 2 == 0 and current_step_id > 2:    
                                rename_builder_files(game_id, current_step_id)
                                print('For step {} we need to rename the blob file, because it is builder')             
                else:
                    #if games:
                    print('Waiting on results for hits results...')
                    t.sleep(60)
                    #else:
                    #  sys.exit("No more games to play")  

def re_create_turk_job(table_hits, table_games):
    #Need to do: move it to args all these hard-coded variables
    is_it_initial = True
    max_num_steps_game = 30
    games = {}
    results = {}
    #games[(current_attempt_id, structure_id)] = {"latest_hit": None}
    with TableClient.from_connection_string(conn_str=connect_str_key, table_name=table_games) as table_client_games:
        with TableClient.from_connection_string(conn_str=connect_str_key, table_name=table_hits) as table_client_hits:
            if is_it_initial:
                is_it_initial = False
                results = get_complete_assignments()
                #print("Results are {}".format(results))
                if results:
                    print('Retrieving some submitted hits results')
                    for game_hit_id in results.keys():
                            query_filter = "RowKey eq '{}'".format(game_hit_id)
                            try:
                                entities = table_client_hits.query_entities(query_filter=query_filter, select=["StepId", "structureId", "attemptId"])
                                for item in entities:
                                    attempt_id = item["attemptId"]
                                    structure_id = item["structureId"]
                                    ###just for now
                                    if attempt_id == 1:
                                       games[(attempt_id, structure_id)] = {"latest_hit": game_hit_id}
                            except ResourceExistsError: 
                                print('StepId  and structureId  is outside of the scope')
                    process_results(max_num_steps_game, results, games, table_client_games, table_client_hits)  
            while games: 
                print('Detected unfinished games')           
                if results:
                    results = get_complete_assignments()            
                    process_results(max_num_steps_game, results, games, table_client_games, table_client_hits)    
                else:
                    #if games:
                    print('Waiting on results for hits results yet...')
                    t.sleep(60)

def process_results(max_num_steps_game, results, games, table_client_games, table_client_hits):
    for (attempt_id, structure_id), game_info in dict(games).items():
            game_id = create_game_id(attempt_id, structure_id) 
            game_hit_id = game_info["latest_hit"]
            game_hit_result = results[game_hit_id]
            try:
                print('Partition is {} and row key is {}'.format(game_id,game_hit_id))
                merged_entity = table_client_hits.get_entity(partition_key=game_id, row_key=game_hit_id)
            except ResourceExistsError: 
                print('HIT {} is outside of the scope'.format(game_hit_result))  
            for answer in game_hit_result:
                    merged_entity[answer] = game_hit_result[answer]

            for item in merged_entity:
                    print('Mehtod: create_mturk_job(): entity: Key is {} and value is {}'.format(item, merged_entity[item]))

            table_client_hits.upsert_entity(mode=UpdateMode.MERGE, entity=merged_entity)
            print("New entity completed {} in inserted: input and output for the hit".format(merged_entity))    

            if results[game_hit_id]['IsHITQualified'] == True:
                            #proceed as valid turk
                current_step_id = merged_entity["StepId"] + 1  # incremeting step id to go to next step in game
                create_new_hit(
                                max_num_steps_game, 
                                games, 
                                table_client_games,
                                table_client_hits, 
                                attempt_id, 
                                structure_id, 
                                game_info, 
                                game_id, 
                                merged_entity, 
                                current_step_id) 
                                
            else:
                current_step_id = merged_entity["StepId"] # no incrementation is happening 
                                #re-crete the same HIT as on previous step
                re_create_hit(
                                    table_client_hits, 
                                    attempt_id, 
                                    structure_id, 
                                    game_info, 
                                    game_id, 
                                    merged_entity,
                                    current_step_id)
                if current_step_id % 2 == 0 and current_step_id > 2:    
                    rename_builder_files(game_id, current_step_id)
                    print('For step {} we need rename the blob file, because it builder')
                    #else:
                    #  sys.exit("No more games to play")


def get_previous_entity (table_client_hits, game_id, current_step_id):
    query_filter = "PartitionKey eq '{}' and StepId eq {} and IsHITQualified eq 'true'".format(game_id, current_step_id-1)
    print('query filter {}'.format(query_filter))
    try:
        print('Partition is {} and row key is {}'.format(game_id))
        return table_client_hits.query_entities(query_filter=query_filter)
    except ResourceExistsError: 
        print('GameId {} and StepId {} is outside of the scope'.format(game_id, current_step_id))


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

    if "architect" in merged_entity["Role"]:
        if (merged_entity["IsBuiltStructureComplete"] == 'yes' and merged_entity['IsHITQualified'] == True) or merged_entity["StepId"] > max_num_steps_game:
            del games[(attempt_id, structure_id)]
            #add here change of the game status
            #game_id = create_game_id(current_attempt_id, structure_id)
            finished_game_entity = {
                        "PartitionKey": structure_id,
                        "RowKey": attempt_id, #RowKey is attempt id
                        "gameId": game_id,
                        "started": 'yes',
                        "finished": 'yes',
                    }  
            print('GameId {} is finished '.format(game_id))
            try:        
                table_client_games.upsert_entity(mode=UpdateMode.MERGE,entity=finished_game_entity)
                print('Successfully inserted the new entity {} into gameIds table'.format(finished_game_entity))
            except ResourceExistsError:
                print("Entity {} already exists!".format(game_id))   
            
        else:
           
            if merged_entity["Role"] == 'architect-normal':
               game_info["latest_hit"] = create_builder_normal(
                                                                table_client_hits, 
                                                                attempt_id, 
                                                                structure_id, 
                                                                game_id, 
                                                                merged_entity, 
                                                                current_step_id,
                                                                builder_data_path)
                                    
            elif merged_entity["Role"] == 'architect-cq':
                game_info["latest_hit"] = create_builder_cq(
                                                            table_client_hits, 
                                                            attempt_id, 
                                                            structure_id, 
                                                            game_id, 
                                                            merged_entity, 
                                                            current_step_id,
                                                            builder_data_path)  
    elif "builder" in merged_entity["Role"]:
            if merged_entity["Role"] == 'builder-normal' and merged_entity["IsInstructionClear"] == 'No' and merged_entity['ClarifyingQuestion'] is not None:
               game_info["latest_hit"] = create_architect_cq(
                                                            table_client_hits, 
                                                            attempt_id, 
                                                            structure_id, 
                                                            game_id, 
                                                            merged_entity, 
                                                            current_step_id,
                                                            builder_data_path)  
            else:
                game_info["latest_hit"] = create_architect_normal(
                                                                table_client_hits, 
                                                                attempt_id, 
                                                                structure_id, 
                                                                game_id, 
                                                                merged_entity,
                                                                current_step_id,
                                                                builder_data_path)
    else:
        print("Something went wrong, the Role is hit is {} and it's unknown".format(merged_entity["Role"]))


def re_create_hit(table_client_hits, attempt_id, structure_id, game_info, game_id, merged_entity, current_step_id):
    if env_var == 'prod':
        builder_data_path = 'builder-data'
    else:
        builder_data_path = 'test-builder-data'

    if "architect" in merged_entity["Role"]:
            if merged_entity["Role"] == 'architect-normal':

               game_info["latest_hit"] = re_create_architect_normal(            table_client_hits, 
                                                                                attempt_id, 
                                                                                structure_id, 
                                                                                game_id, 
                                                                                merged_entity, 
                                                                                current_step_id,
                                                                                builder_data_path,
                                                                                )
                                    
            elif merged_entity["Role"] == 'architect-cq':
                game_info["latest_hit"] = re_create_architect_cq(
                                                                                table_client_hits, 
                                                                                attempt_id, 
                                                                                structure_id, 
                                                                                game_id, 
                                                                                merged_entity, 
                                                                                current_step_id,
                                                                                builder_data_path)  
    elif "builder" in merged_entity["Role"]:
            if merged_entity["Role"] == 'builder-normal':
               game_info["latest_hit"] = re_create_builder_normal(
                                                                table_client_hits, 
                                                                attempt_id, 
                                                                structure_id, 
                                                                game_id, 
                                                                merged_entity, 
                                                                current_step_id,
                                                                builder_data_path)  
            else:
                game_info["latest_hit"] = re_create_builder_cq(
                                                                table_client_hits, 
                                                                attempt_id, 
                                                                structure_id, 
                                                                game_id,
                                                                merged_entity,  
                                                                current_step_id,
                                                                builder_data_path)  
    else:
        print("Something went wrong, the Role is hit is {} and it's unknown".format(merged_entity["Role"]))

def create_architect_normal(table_client_hits, attempt_id, structure_id, game_id, merged_entity, current_step_id, builder_data_path):
    print("Creating architect-normal. Done!")
    new_hit_type = "architect-normal"
    hit_input = {}
    template = create_template_given_type(
                                          new_hit_type, 
                                          structureId=structure_id, 
                                          screenshotPath=create_screenshot_path_till_view(game_id,current_step_id-1),
                                          north='north',
                                          south='south',
                                          west='west',
                                          east='east',
                                          top='top',
                                          builderDataPath=builder_data_path
                                        )
    new_hit_id = create_hit_given_type_template(new_hit_type, template) 
    hit_input['InputScreenshotPath'] = create_screenshot_path_till_view(game_id,current_step_id-1)
    #print('Current Row4new HIT {} {} {} {} {} {} '.format(table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, new_hit_type))               
    create_new_row4new_hit(
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            current_step_id, 
                            new_hit_id,
                            new_hit_type,
                            hit_input,
                            merged_entity)
    return new_hit_id 

def re_create_architect_normal(table_client_hits, attempt_id, structure_id, game_id, merged_entity, current_step_id, builder_data_path):
    new_hit_type = "architect-normal"
    hit_input = {}
    template = create_template_given_type(
                                          new_hit_type, 
                                          structureId=structure_id, 
                                          screenshotPath=merged_entity['InputScreenshotPath'],
                                          builderDataPath=builder_data_path,
                                          north='north',
                                          south='south',
                                          west='west',
                                          east='east',
                                          top='top'
                                        )
    new_hit_id = create_hit_given_type_template(new_hit_type, template) 
    hit_input['InputScreenshotPath'] = merged_entity['InputScreenshotPath']
    #print('Current Row4new HIT {} {} {} {} {} {} '.format(table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, new_hit_type))               
    create_new_row4new_hit(
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            current_step_id, 
                            new_hit_id,
                            new_hit_type,
                            hit_input,
                            merged_entity)
    print("Re-creation of architect-normal new_hit_id {} new_hit_type {} current_step_id {}.  Done!".format(new_hit_id, new_hit_type, current_step_id))
    return new_hit_id                                      


def create_architect_cq(table_client_hits, attempt_id, structure_id, game_id, merged_entity, current_step_id, builder_data_path):
    print("Creating architect-cq game id {} current step i {} ".format(game_id, current_step_id))
    new_hit_type = "architect-cq"
    hit_input = {}
    entities_prev_architect = get_previous_step_in_game(
                                                        table_client_hits, 
                                                        game_id, 
                                                        current_step_id, 
                                                        delta=2,
                                                        type='architect-normal'
                                                        )                                                  

    previously_picked_view = entities_prev_architect["views"]
    previous_instruction = entities_prev_architect["instruction"]
    question = merged_entity["ClarifyingQuestion"]         

    template = create_template_given_type(
                                        new_hit_type, 
                                        structureId=structure_id, 
                                        screenshotPath=create_screenshot_path_till_view(game_id, current_step_id-3),
                                        screenshotView=previously_picked_view, 
                                        previousInstr=previous_instruction, 
                                        ClarifyingQuestion=question,
                                        builderDataPath= builder_data_path,
                                        north='north',
                                        south='south',
                                        west='west',
                                        east='east',
                                        top='top',
                                        )                               
    
    hit_input['InputViews'] = previously_picked_view
    hit_input['InputInstruction'] = previous_instruction 
    hit_input['InputClarifyingQuestion'] = question
    hit_input['InputScreenshotPath'] = create_screenshot_path_till_view(game_id, current_step_id-3)
    new_hit_id = create_hit_given_type_template(new_hit_type, template)
    #print('create_template_given_type: Current Row4new HIT {} {} {} {} {} {} {}'.format(
    #    table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, new_hit_type, hit_input))  

    create_new_row4new_hit(
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            current_step_id,
                            new_hit_id,
                            new_hit_type,
                            hit_input,
                            merged_entity)
                                   
    return new_hit_id                                           

def re_create_architect_cq(table_client_hits, attempt_id, structure_id, game_id, merged_entity, current_step_id, builder_data_path):
    new_hit_type = "architect-cq"
    hit_input = {}
                                                 
    previously_picked_view = merged_entity["InputViews"]
    previous_instruction = merged_entity["InputInstruction"]
    question = merged_entity["InputClarifyingQuestion"]
    screenshot_view = merged_entity["InputScreenshotPath"]         

    template = create_template_given_type(
                                        new_hit_type, 
                                        structureId=structure_id, 
                                        screenshotPath=screenshot_view,
                                        screenshotView=previously_picked_view, 
                                        builderDataPath=builder_data_path,
                                        previousInstr=previous_instruction, 
                                        ClarifyingQuestion=question,
                                        north='north',
                                        south='south',
                                        west='west',
                                        east='east',
                                        top='top',
                                        )                               

    new_hit_id = create_hit_given_type_template(new_hit_type, template)
    #print('Current Row4new HIT {} {} {} {} {} {} '.format(table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, new_hit_type))  

    hit_input['InputViews'] = previously_picked_view
    hit_input['InputInstruction'] = previous_instruction 
    hit_input['InputClarifyingQuestion'] = question
    hit_input['InputScreenshotPath'] = screenshot_view

    create_new_row4new_hit(
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            current_step_id,
                            new_hit_id, 
                            new_hit_type,
                            hit_input,
                            merged_entity)
    print("Re-creation of architect-cq new_hit_id {} game_id {} current_step_id {}. Done!".format(new_hit_id, game_id, current_step_id))
    return new_hit_id

def create_builder_cq(table_client_hits, attempt_id, structure_id, game_id, merged_entity, current_step_id, builder_data_path):
    print('Creating builder-cq')
    new_hit_type = "builder-cq"
    hit_input = {} 
    prev_builder_step = current_step_id - 2 # decide -4 or -2
    screenshot_path=create_screenshot_path_till_view(game_id, prev_builder_step)
    print('create_builder_cq, and the current step is {}'.format(current_step_id))

    entities_prev_prev_architect = get_previous_step_in_game(
                                        table_client_hits,
                                        game_id,
                                        current_step_id, 
                                        delta=3,
                                        type='architect-normal')

    entities_prev_architect = get_previous_step_in_game(
                                        table_client_hits,
                                        game_id,
                                        current_step_id, 
                                        delta=1,
                                        type='architect-cq')

    entities_prev_builder = get_previous_step_in_game(
                                        table_client_hits, 
                                        game_id, 
                                        current_step_id, 
                                        delta=2,
                                        type='builder')

    template = create_template_given_type(
                                        new_hit_type,
                                        gameId=game_id, 
                                        clarifyingQuestion=entities_prev_builder["ClarifyingQuestion"], 
                                        answer=entities_prev_architect["Answer4ClarifyingQuestion"],
                                        prevStep=prev_builder_step, 
                                        currentStep=current_step_id,
                                        builderDataPath=builder_data_path,
                                        screenshotPath=screenshot_path,
                                        instruction=entities_prev_prev_architect["instruction"],
                                        screenshotView=entities_prev_prev_architect["views"],
                                        sas=sas,
                                        )
    new_hit_id = create_hit_given_type_template("builder-cq", template)
    # print('Current Row4new HIT {} {} {} {} {} {} ', table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, new_hit_type) 
    # print('next printing the builder-cq template')
    # print(template)

    hit_input['InputViews'] = entities_prev_prev_architect["views"]
    hit_input['InputInstruction'] = entities_prev_prev_architect["instruction"]
    hit_input['InputClarifyingQuestion'] = entities_prev_builder["ClarifyingQuestion"]
    hit_input['InputAnswer4ClarifyingQuestion'] = entities_prev_builder["ClarifyingQuestion"] 
    hit_input['InputScreenshotPath'] = screenshot_path

    create_new_row4new_hit(
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            current_step_id,
                            new_hit_id,
                            new_hit_type,
                            hit_input,
                            merged_entity)                                  
    return new_hit_id

def re_create_builder_cq(table_client_hits, attempt_id, structure_id, game_id, merged_entity, current_step_id, builder_data_path):
    new_hit_type = "builder-cq"
    hit_input = {} 

    template = create_template_given_type(
                                        new_hit_type,
                                        gameId=game_id, 
                                        clarifyingQuestion=merged_entity["InputClarifyingQuestion"], 
                                        answer=merged_entity["InputAnswer4ClarifyingQuestion"],
                                        prevStep=current_step_id - 2, 
                                        currentStep=current_step_id,
                                        builderDataPath=builder_data_path,
                                        screenshotPath=merged_entity['InputScreenshotPath'],
                                        instruction=merged_entity["InputInstruction"],
                                        screenshotView=merged_entity["InputViews"],
                                        sas=sas,
                                        )
    new_hit_id = create_hit_given_type_template("builder-cq", template)
    #print('Current Row4new HIT {} {} {} {} {} {} ', table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, new_hit_type) 

    hit_input['InputViews'] = merged_entity["InputViews"]
    hit_input['InputInstruction'] = merged_entity["InputInstruction"]
    hit_input['InputClarifyingQuestion'] = merged_entity["InputClarifyingQuestion"]
    hit_input['InputAnswer4ClarifyingQuestion'] = merged_entity["InputAnswer4ClarifyingQuestion"]
    hit_input['InputScreenshotPath'] = merged_entity['InputScreenshotPath']

    create_new_row4new_hit(
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            current_step_id,
                            new_hit_id,
                            new_hit_type,
                            hit_input,
                            merged_entity)      
    print("Re-creation of builder-cq new_hit_id {} game_id {} current_step_id {}. Done!".format(new_hit_id, game_id, current_step_id))            
    return new_hit_id


def create_builder_normal(table_client_hits, attempt_id, structure_id, game_id, merged_entity, current_step_id, builder_data_path):
    template = ''
    new_hit_type = "builder-normal"
    hit_input = {}
    #INPUT: $gameId, $currentStep, $prevStep, $instruction, $screenshotPath, $screenshotView
    #for cases of newly initialized games

    if current_step_id - 2 == 0: 
        hit_input['InputScreenshotPath'] = 'default/view_'
        template = create_template_given_type(
                                        new_hit_type, 
                                        instruction=merged_entity["instruction"], 
                                        gameId=game_id, 
                                        prevStep=current_step_id,
                                        currentStep=current_step_id,
                                        builderDataPath=builder_data_path,
                                        screenshotPath='default/view_',
                                        screenshotView=merged_entity["views"],
                                        sas=sas,
                                        )

    else:
        hit_input['InputScreenshotPath'] = create_screenshot_path_till_view(game_id,current_step_id-2)
        template = create_template_given_type(
                                        new_hit_type,
                                        instruction=merged_entity["instruction"],
                                        gameId=game_id, 
                                        prevStep=current_step_id-2,
                                        currentStep=current_step_id,
                                        builderDataPath=builder_data_path,
                                        screenshotPath=create_screenshot_path_till_view(game_id,current_step_id-2),
                                        screenshotView=merged_entity["views"],
                                        sas=sas,
                                        )

    new_hit_id = create_hit_given_type_template(new_hit_type, template)

    hit_input['InputViews'] = merged_entity["views"]
    hit_input['InputInstruction'] = merged_entity["instruction"] 
    print('Rendering builder-normal template')
    # print(template)

    #print('Current Row4new HIT {} {} {} {} {} {} '.format(table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, new_hit_type))               
    create_new_row4new_hit(
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            current_step_id, 
                            new_hit_id,
                            new_hit_type,
                            hit_input,
                            merged_entity) 
    print('Done creating builder-normal')
    return new_hit_id 

def re_create_builder_normal(table_client_hits, attempt_id, structure_id, game_id, merged_entity, current_step_id, builder_data_path):
    template = ''
    hit_type = "builder-normal"
    hit_input = {}
  
    template = create_template_given_type(
                                    hit_type,
                                    instruction=merged_entity["InputInstruction"],
                                    gameId=game_id, 
                                    prevStep=current_step_id-2,
                                    currentStep=current_step_id,
                                    builderDataPath=builder_data_path,
                                    screenshotPath=merged_entity["InputScreenshotPath"],
                                    screenshotView=merged_entity["InputViews"],
                                    sas=sas,
                                    )
                                    
    hit_input['InputViews'] = merged_entity["InputViews"]
    hit_input['InputInstruction'] = merged_entity["InputInstruction"]
    hit_input['InputScreenshotPath'] = merged_entity['InputScreenshotPath']   

    new_hit_id = create_hit_given_type_template(hit_type, template)
    #print('Current Row4new HIT {} {} {} {} {} {} '.format(table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, hit_type))               
    create_new_row4new_hit(
                            table_client_hits, 
                            attempt_id, 
                            structure_id, 
                            current_step_id, 
                            new_hit_id, 
                            hit_type,
                            hit_input,
                            merged_entity) 

    print("Re-creation of builder-normal new_hit_id {} game_id {} current_step_id {}.Done!".format(new_hit_id, game_id, current_step_id))
    return new_hit_id     

def get_previous_step_in_game(table_client_hits, game_id, current_step_id, delta, type):
    if current_step_id - delta > 0:
        retrieved_entities = {}
        query_filter = "PartitionKey eq '{}' and StepId eq {}".format(game_id, current_step_id-delta)
        print('query filter {}'.format(query_filter))
        if "architect-normal" in type:
            try:
                entities = table_client_hits.query_entities(query_filter=query_filter, select=["instruction", "views"])
                for item in entities:
                    print('get_previous_step_in_game if architect-normal: item {} '.format(item))
                    print('get_previous_step_in_game: Views are {}'.format(item.get("views")))
                    retrieved_entities["views"] = item.get("views")
                    print('get_previous_step_in_game: Instruction are {}'.format(item.get("instruction")))
                    retrieved_entities["instruction"] = item.get("instruction")
            except HttpResponseError as e:
                    print(e.message)
        elif  "architect-cq" in type:
                try:
                    entities = table_client_hits.query_entities(query_filter=query_filter, select=["Answer4ClarifyingQuestion"])
                    for item in entities:
                        print('get_previous_step_in_game if architect-cq: item {} '.format(item))
                        print('get_previous_step_in_game: Views are {}'.format(item.get("Answer4ClarifyingQuestion")))
                        retrieved_entities["Answer4ClarifyingQuestion"] = item.get("Answer4ClarifyingQuestion")
                        
                except HttpResponseError as e:
                        print(e.message)

        elif  "builder" in type:
            try:
                entities = table_client_hits.query_entities(query_filter=query_filter, select=["ClarifyingQuestion"])
                for item in entities:
                    print('get_previous_step_in_game if builder: item {} '.format(item))
                    print('get_previous_step_in_game: Views are {}'.format(item.get("ClarifyingQuestion")))
                    retrieved_entities["ClarifyingQuestion"] = item.get("ClarifyingQuestion")
            except HttpResponseError as e:
                    print(e.message)
        else:
            print('Exception: method get_previous_step_in_game(), provided hit type [{}] is not supported'.format(type))                            
        return retrieved_entities  
    else:
        print("Something went wrong, the current_step_id:{} - 2 < 0".format(current_step_id))


def create_new_row4new_hit(table_client_hits, attempt_id, structure_id, current_step_id, new_hit_id, hit_type, hit_input, merged_entity):
    entity_to_insert = {}
    entity = {
            "PartitionKey": create_game_id(attempt_id, structure_id),
            "RowKey": new_hit_id, 
            "StepId": current_step_id,
            "structureId": structure_id,
            "attemptId": attempt_id,
            "Role": hit_type,
            "IsStructureCompleteFlag": merged_entity['IsStructureCompleteFlag']
            }
    if  len(hit_input) == 0:
        entity_to_insert = entity   
    else: 
        entity_to_insert = merge_dicts(entity, hit_input)     
        print('The length of hit_input is {} and dict to insert is {}'.format(len(hit_input), entity_to_insert)) 
    try:        
        table_client_hits.create_entity(entity_to_insert)
        print('Successfully inserted the new entity into table ')
    except ResourceExistsError:
        # TODO: throw or assert or something: this is an error
        print("Entity {hitId} already exists!".format(hitId=new_hit_id))

def merge_dicts(x, y):
    # print("x is {} and y is {}".format(x, y))
    if len(y) > 0: 
       z = x.copy() # start with x's keys and values
       z.update(y) # modify z with y's keys and values
    #    print("x is {} and y is {} and resulted z is {}".format(x, y, z))
       return z
    else:
        return x   

def create_screenshot_path_till_view(game_id, step_id):
    if env_var == 'prod':
        builder_folder = 'builder-data'
    else:
        builder_folder = 'test-builder-data'

    if  (step_id % 2) == 1: 
        # TODO make into an error
        print('Something went wrong: step id cannot be odd number'.format(step_id))
    elif step_id == 0:
        return "default/view_"    
    else:
        print("The path to builder intermediate world is [/{}/{}/step-{}]".format(builder_folder,game_id,step_id))    
        return "{}/step-{}_".format(game_id, step_id)                    


def init_hits(games, table_client_hits):
    if env_var == 'prod':
        builder_data_path = 'builder-data'
    else:
        builder_data_path = 'test-builder-data'
    for attempt_id, structure_id in games:
        game_id = create_game_id(attempt_id, structure_id)
        template = create_template_given_type(
            type_hit='architect-normal',
            gameId=game_id, 
            structureId=structure_id, 
            screenshotPath='default/view_',
            north='north',
            south='south',
            west='west',
            east='east',
            top='top',
            builderDataPath = builder_data_path)
        #print('Attempt to create Hit; the template is {}'.format(template))
        #print('Attempt to create Hit for {}-{}'.format(attempt_id, structure_id))  
        print('Hit initialized for game: {}'.format(game_id))
        hit_id = create_hit_given_type_template('architect-normal', template)
        games[(attempt_id, structure_id)]["latest_hit"] = hit_id
        step_id = 1
        hit_entity = {
                        "PartitionKey": create_game_id(attempt_id, structure_id),
                        "RowKey": hit_id, 
                        "StepId": step_id,
                        "structureId": structure_id,
                        "attemptId": attempt_id,
                        "Role": 'architect-normal',
                        "InputScreenshotPath": 'default/view_',
                        "IsStructureCompleteFlag": 0
                    }
        try:        
            table_client_hits.create_entity(hit_entity)
            print('Successfully inserted the new entity {} into table_client_hits'.format(hit_entity))
        except ResourceExistsError:
            print("Entity {hitId} already exists!".format(hitId=hit_entity))           


def initialize_new_games(path_target_ids, table_games, table_client_games):
    games = {} 
    structure_ids = list_structure_ids(path_target_ids)
    for structure_id in structure_ids:
        query_filter = "PartitionKey eq '{structureId}'".format(structureId=structure_id)
        print("StructureId eq '{structureId}'".format(structureId=structure_id))
        entities = list(table_client_games.query_entities(
            query_filter=query_filter, 
            select='RowKey'))
        #print("Entities: {!r}".format(entities))    
        current_attempt_id = 1    
        if  entities:   
            listRowKeys = []
            for item in entities:
                listRowKeys.append(int(item['RowKey']))
            current_attempt_id = max(listRowKeys) + 1    

        print('Current attempt id is {}'.format(current_attempt_id))    
        game_id = create_game_id(current_attempt_id, structure_id)
        game_entity = {
                    "PartitionKey": structure_id,
                    "RowKey": current_attempt_id, #RowKey is attempt id
                    "gameId": game_id,
                    "started": 'yes',
                    "finished": 'no'
                }    
        games[(current_attempt_id, structure_id)] = {"latest_hit": None}
        #print('Inserting a new entity {} into table {}'.format(game_entity, table_games))
        try:        
            table_client_games.upsert_entity(mode=UpdateMode.MERGE,entity=game_entity)
            print('Successfully inserted the new entity {} into table {}'.format(game_entity, table_games))
        except ResourceExistsError:
            print("Entity {} already exists!".format(game_id))
    return games                

def get_remaining_active_games(newly_initiated_games, table_client_games):
    games = {} 
    date_considered = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    query_filter = "Timestamp ge datetime'{dateConsidered}' and finished eq 'no'".format(dateConsidered = date_considered)
    entities = list(table_client_games.query_entities(
        query_filter=query_filter, 
        select='gameId')) 
    if  entities:
        print('Other active games:')
        for item in entities:
            attempt_id = int(item['gameId'].split('-')[0])
            structure_id = item['gameId'].split('-')[1]
            if (attempt_id, structure_id) not in newly_initiated_games:
                games[(attempt_id, structure_id)] = {"latest_hit": None}
                print((attempt_id, structure_id))
    return games

def update_games_latest_hit(remaining_active_games, table_client_hits):
    remaining_active_games_dict = remaining_active_games
    games_latest_hit = {}
    keys_to_delete = []
    for (attempt_id, structure_id) in remaining_active_games_dict:
        game_id = create_game_id(attempt_id, structure_id)
        try:
            query_filter = "PartitionKey eq '{gameId}'".format(gameId = game_id)
            hit_entities = list(table_client_hits.query_entities(
            query_filter=query_filter)) 
        except ResourceExistsError: 
            print('Game {} not found in Hits Table'.format(game_id))  
        for row in hit_entities:
            attempt_id = row['attemptId']
            structure_id = row['structureId']
            cur_step_id = int(row['StepId'])
            cur_hit_id = row['RowKey']
            if (attempt_id, structure_id) not in games_latest_hit:
                games_latest_hit[(attempt_id, structure_id)] = (cur_step_id, cur_hit_id)
            elif games_latest_hit[(attempt_id, structure_id)][0] < cur_step_id:
                games_latest_hit[(attempt_id, structure_id)] = (cur_step_id, cur_hit_id)
    for game_key_id in remaining_active_games_dict:
        try:
            remaining_active_games_dict[game_key_id] = {"latest_hit": games_latest_hit[game_key_id][1]}
        except KeyError: 
            print('Game {} not found in Hits Table.Ignoring game id for updating latest hit'.format(game_key_id))
            keys_to_delete.append(game_key_id)
    for key in keys_to_delete:
        del remaining_active_games_dict[key]
    return remaining_active_games_dict

def create_tables_if_not_exist(table_hits, table_games):
    print("Creating table for hits is [{}]".format(table_hits))
    print("Creating Table for games is [{}]".format(table_games))

    with TableServiceClient.from_connection_string(connect_str_key) as table_service_client:
             table_service_client.create_table_if_not_exists(table_name = table_games)
             print("Table for games is {} is successfully created".format(table_games))
             table_service_client.create_table_if_not_exists(table_name = table_hits)
             print("Table for hits is {} is successfully created".format(table_hits))
       

if __name__ == "__main__":
 ## Creating qualification tests -- need to do it only once, main purpose is to display consent form 
    # create_qualification_test('architect')
    # create_qualification_test('builder')
    # create_qualification_test('merged') #current id is 3FIQMFNPAF983ZZ6YSKHSCP7UKFN6Q
    # create_qualification_test('reduced') # in sandbox 3EJZW0TH3GUNEXVCXI1CABUNPVZ96E, in prod 3SR1M7GDJ3VD1FMG2M7X345A544A2K

    #parser = argparse.ArgumentParser()
    #parser.add_argument(
       
    #)
    #parser.add_argument(
    #    "--mode",
    #    description="sandbox or prod",
    #    type=str,
    #    required=True
    #)
    #args = parser.parse_args()
    #create_turk_job(args.xml_file, args.input_csv)


## Main Task Creation
    ##if sandbox 
    #table_hits = "TestHitsTable"
    #table_games = "TestGameIds" 
    #path_target_ids = 'test_list_game_ids.txt'
    ## if prod 
    env_var = sys.argv[1]
    path_target_ids = sys.argv[2]
    max_num_steps = int(sys.argv[3])
    
    #'test_list_game_ids.txt'

    if env_var == 'prod':
        table_hits = "HitsTable"
        table_games = "GameIds"
    elif env_var == 'sandbox':
        table_hits = "TestHitsTable"
        table_games = "TestGameIds"
    #re_create_turk_job(table_hits, table_games)

    create_turk_job(table_hits, table_games, path_target_ids, max_num_steps)
  
    ###Testing separate methods
    #print(is_English('pvfvgnhg'))
    #rename_builder_files('12-c161', '2')

    #parser = argparse.ArgumentParser()
    #parser.add_argument(
       
    #)
    #parser.add_argument(
    #    "--input_csv",
    #    description="Path to input CSV file containing Turk task parameters",
    #    type=str,
    #    required=True
    #)
    #args = parser.parse_args()
    #create_turk_job(args.xml_file, args.input_csv)