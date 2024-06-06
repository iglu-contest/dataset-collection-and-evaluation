import argparse
import os
import sys
import boto3
import dotenv


def read_args():
    parser = argparse.ArgumentParser(
        description='Create a qualifier in Mturk.')
    parser.add_argument(
        '--qualifier_questions', type=str,
        default='qualifier-questions.xml', help='Filepath with the qualifier questions.')
    parser.add_argument(
        '--qualifier_answer_key', type=str,
        default='qualifier-questions.xml', help='Filepath with the qualifier answers.')
    parser.add_argument(
        '--config', choices=['production', 'sandbox'], default='sandbox',
        help='Environment to use for operations')
    parser.add_argument(
        '--env_filepath', type=str, default='.env',
        help='Path to .env file with environment variables AWS_ACCESS_KEY_ID. '
             'and AWS_SECRET_ACCESS_KEY, in case they are not already set.')
    return parser.parse_args()


def main():
    args = read_args()

    with open(args.qualifier_questions) as questions_file:
        questions_xml = questions_file.read()

    with open(args.qualifier_answer_key) as questions_file:
        answers_xml = questions_file.read()

    dotenv.load_dotenv(args.env_filepath)

    # Create task
    if args.config == 'production':
        endpoint_url = 'https://mturk-requester.us-east-1.amazonaws.com'
    elif args.config == 'sandbox':
        endpoint_url = 'https://mturk-requester-sandbox.us-east-1.amazonaws.com'
    else:
        print('Incorrect environment')
        exit(1)

    mturk = boto3.client(
        'mturk', region_name='us-east-1', endpoint_url=endpoint_url,
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID', ''),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY', ''),
    )

    description = (
        "This is a brief description of the game's rules with examples of how "
        "the HIT will look like. It also includes a consent form that should be approved, "
        "otherwise we cannot collect data from your HIT.")

    qual_response = mturk.create_qualification_type(
        Name='iglu-minecraft-eval-qualifier',
        Keywords='minecraft, artificial intelligence, building, instructions, natural language',
        Description=description,
        QualificationTypeStatus='Active',
        Test=questions_xml,
        AnswerKey=answers_xml,
        TestDurationInSeconds=600)

    print("New qualifier created with name:")
    print(qual_response['QualificationType']['QualificationTypeId'])


if __name__ == '__main__':
    main()