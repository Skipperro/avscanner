import time
import boto3
import os
import zipfile
import pyclamd

awskey = os.environ['ACCESS_KEY']
awssecret = os.environ['SECRET_KEY']

uploaded_bucket = os.environ['UPLOAD_BUCKET']
clean_bucket = os.environ['CLEAN_BUCKET']
infected_bucket = os.environ['INFECTED_BUCKET']


def get_s3_session():
    session = boto3.Session(aws_access_key_id=awskey, aws_secret_access_key=awssecret)
    return session


def get_bucket_keys(bucket):
    output = []
    try:
        session = get_s3_session()
        client = session.client('s3')
        objects = client.list_objects(Bucket=bucket)
        for key in objects['Contents']:
            if not key['Key'].endswith('/'):
                output.append(key['Key'])
    except:
        pass
    return output


def remove_from_s3(bucket, key):
    try:
        print(f'Removing file {key} from {bucket}...')
        session = get_s3_session()
        client = session.client('s3')
        key_root = key.split('/')[0]
        client.delete_object(Bucket=bucket, Key=key)
        client.delete_object(Bucket=bucket, Key=key_root)
        client.delete_object(Bucket=bucket, Key=f'{key_root}/')
        print(f'File {key} removed successfully.')
    except Exception as e:
        raise Exception(f"Error removing file from S3: {e}")

def move_file_between_s3_buckets(source_bucket, source_key, destination_bucket):
    try:
        print(f'Moving file {source_key} to {destination_bucket}...')
        session = get_s3_session()
        client = session.client('s3')
        client.copy_object(CopySource={'Bucket': source_bucket, 'Key': source_key}, Bucket=destination_bucket,
                           Key=source_key)
        source_root = source_key.split('/')[0]
        client.delete_object(Bucket=source_bucket, Key=source_key)
        client.delete_object(Bucket=source_bucket, Key=source_root)
        client.delete_object(Bucket=source_bucket, Key=f'{source_root}/')
        print(f'File {source_key} moved successfully.')
    except Exception as e:
        raise Exception(f"Error moving file between buckets: {e}")


def download_s3_file(bucket, key, destination_path):
    try:
        print(f'Downloading file {key} from S3...')
        session = get_s3_session()
        client = session.client('s3')
        client.download_file(bucket, key, destination_path)
        print(f'File {key} downloaded successfully.')
    except Exception as e:
        raise Exception(f"Error downloading file from S3: {e}")


def extract_zip_file(zip_file_path, destination_path):
    try:
        print('Extracting zip file...')
        with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
            zip_ref.extractall(destination_path)
        print('Zip file extracted successfully.')
    except Exception as e:
        raise Exception(f"Error extracting zip file: {e}")


def delete_file(file_path):
    try:
        os.remove(file_path)
    except Exception as e:
        raise Exception(f"Error deleting file: {e}")


def delete_folder_recursively(folder_path):
    try:
        print(f'Deleting folder {folder_path} recursively...')
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder_path)
        print(f'Folder {folder_path} deleted successfully.')
    except Exception as e:
        raise Exception(f"Error deleting folder: {e}")


def scan_directory_for_viruses(folder_path):
    # Uses pyclamd to scan the folder for viruses
    # Returns a list of viruses found
    try:
        print(f'Scanning directory {folder_path} for viruses...')
        os.system('service clamav-daemon restart')
        time.sleep(5)
        clam = pyclamd.ClamdUnixSocket()
        if not clam.ping():
            raise Exception("Clamd is not running")
        viruses = clam.multiscan_file(folder_path)
        print(f'Directory {folder_path} scanned successfully.')
        return viruses
    except Exception as e:
        raise Exception(f"Error scanning directory for viruses: {e}")


def process_file(s3key: str):
    #If the s3key doesn't end with .zip, remove the file from the uploaded bucket and return
    if not s3key.lower().endswith('.zip'):
        remove_from_s3(uploaded_bucket, s3key)
        return

    # Downloads the file from S3
    if not os.path.exists('./downloaded'):
        os.makedirs('./downloaded')
    download_s3_file(uploaded_bucket, s3key, f'./downloaded/downloaded.zip')

    # Extracts the file
    if not os.path.exists('./extracted'):
        os.makedirs('./extracted')
    extract_zip_file(f'./downloaded/downloaded.zip', './extracted/')
    delete_folder_recursively('./downloaded')

    # Scans the file for viruses
    viruses = scan_directory_for_viruses(os.path.abspath('./extracted/'))
    delete_folder_recursively('./extracted')
    if viruses:
        # Moves the file to the infected bucket
        move_file_between_s3_buckets(uploaded_bucket, s3key, infected_bucket)
        print(f'File {s3key} infected.')
    else:
        # Moves the file to the clean bucket
        move_file_between_s3_buckets(uploaded_bucket, s3key, clean_bucket)
        print(f'File {s3key} clean.')


def scanloop():
    bucket_keys = get_bucket_keys(uploaded_bucket)
    if len(bucket_keys) > 0:
        os.system('freshclam')
        os.system('service clamav-daemon restart')
        time.sleep(5)
        clam = pyclamd.ClamdUnixSocket()
        if not clam.ping():
            raise Exception("Clamd is not running")
        # Process the files in the bucket
        for s3key in get_bucket_keys(uploaded_bucket):
            process_file(s3key)
    else:
        print('No files to process. Sleeping for 30 seconds.')
        time.sleep(30)


def initial_check():
    if not "ACCESS_KEY" in os.environ.keys() or os.environ['ACCESS_KEY'] == '':
        raise Exception("ACCESS_KEY variable is missing!")
    print(f'Access Key: {os.environ["ACCESS_KEY"][:5]}')
    if not "SECRET_KEY" in os.environ.keys() or os.environ['SECRET_KEY'] == '':
        raise Exception("SECRET_KEY variable is missing!")
    print(f'Secret Key: {os.environ["SECRET_KEY"][:5]}')
    if not "UPLOAD_BUCKET" in os.environ.keys() or os.environ['UPLOAD_BUCKET'] == '':
        raise Exception("UPLOAD_BUCKET variable is missing!")
    print(f'Upload Bucket: {os.environ["UPLOAD_BUCKET"]}')
    if not "CLEAN_BUCKET" in os.environ.keys() or os.environ['CLEAN_BUCKET'] == '':
        raise Exception("CLEAN_BUCKET variable is missing!")
    print(f'Clean Bucket: {os.environ["CLEAN_BUCKET"]}')
    if not "INFECTED_BUCKET" in os.environ.keys() or os.environ['INFECTED_BUCKET'] == '':
        raise Exception("INFECTED_BUCKET variable is missing!")
    print(f'Infected Bucket: {os.environ["INFECTED_BUCKET"]}')


if __name__ == '__main__':
    try:
        initial_check()
    except Exception as ex:
        print(ex)
        time.sleep(10)
        exit(1)
    # Loop through the scanloop until the program is killed
    while True:
        try:
            scanloop()
        except KeyboardInterrupt:
            print('Exiting...')
            break
        except Exception as e:
            print(f'Error: {e}')
            if os.path.exists('./extracted'):
                delete_folder_recursively('./extracted')
            if os.path.exists('./downloaded'):
                delete_folder_recursively('./downloaded')
            print('Sleeping for 90 seconds.')
            time.sleep(90)
            exit(2)
