import os
import time
import json
import requests
from requests_oauthlib import OAuth1
import constants


MEDIA_ENDPOINT_URL = 'https://upload.twitter.com/1.1/media/upload.json'
POST_TWEET_URL = 'https://api.twitter.com/1.1/statuses/update.json'


oauth = OAuth1(constants.CONSUMER_KEY,
               client_secret=constants.CONSUMER_SECRET,
               resource_owner_key=constants.ACCESS_KEY,
               resource_owner_secret=constants.ACCESS_SECRET)


class MediaUpload:

    def __init__(self, file_name, media_category=True):
        '''
        Upload file to twitter
        file_name: -> str
        media_category: True for tweet, False for DM
        objects from this:
            - video_filename
            - total_bytes
            - media_id
            - processing_info
            - media_type
            - media_category
        '''
        self.video_filename = file_name
        self.total_bytes = os.path.getsize(self.video_filename)
        self.media_id = None
        self.processing_info = None
        data_media = {
            'gif'		: 'image/gif',
            'mp4'		: 'video/mp4',
            'jpg'		: 'image/jpeg',
            'webp'		: 'image/webp',
            'png'		: 'image/png',
            'image/gif'	: 'tweet_gif',
            'video/mp4'	: 'tweet_video',
            'image/jpeg': 'tweet_image',
            'image/webp': 'tweet_image',
            'image/png'	: 'tweet_image'
        }
        if file_name.split('.')[-1] in data_media.keys():
            self.media_type = data_media[file_name.split('.')[-1]]
            self.media_category = data_media[self.media_type]
        else:
            raise Exception("sorry, the file format is not supported")
        if media_category == False:
            self.media_category = None

    def upload_init(self):
        '''
        init section
        return media id -> int
        '''
        print('INIT')
        request_data = {
            'command': 'INIT',
            'media_type': self.media_type,
            'total_bytes': self.total_bytes,
            'media_category': self.media_category
        }
        if self.media_category == None:
            del request_data['media_category']

        req = requests.post(url=MEDIA_ENDPOINT_URL,
                            data=request_data, auth=oauth)
        media_id = req.json()['media_id']

        self.media_id = media_id

        print('Media ID: %s' % str(media_id))

        return media_id

    def upload_append(self):
        '''
        append section
        '''
        segment_id = 0
        bytes_sent = 0
        file = open(self.video_filename, 'rb')

        while bytes_sent < self.total_bytes:
            chunk = file.read(1024*1024)

            print('APPEND')

            request_data = {
                'command': 'APPEND',
                'media_id': self.media_id,
                'segment_index': segment_id,

            }

            files = {
                'media': chunk
            }

            req = requests.post(url=MEDIA_ENDPOINT_URL,
                                data=request_data, files=files, auth=oauth)

            if req.status_code < 200 or req.status_code > 299:
                print(req.status_code)
                print("Getting error status code")
                return False
            else:
                segment_id = segment_id + 1
                bytes_sent = file.tell()
                print('%s of %s bytes uploaded' %
                      (str(bytes_sent), str(self.total_bytes)))
                print('Upload chunks complete.')

    def upload_finalize(self):
        '''
        Finalizes uploads and starts video processing
        '''
        print('FINALIZE')

        request_data = {
            'command': 'FINALIZE',
            'media_id': self.media_id
        }

        req = requests.post(url=MEDIA_ENDPOINT_URL,
                            data=request_data, auth=oauth)

        self.processing_info = req.json().get('processing_info', None)
        self.check_status()

    def Tweet(self, tweet):
        '''
        tweet a tweet with media_id
        tweet: -> str
        return tweet id -> int
        '''
        request_data = {
            'status': tweet,
            'media_ids': self.media_id
        }

        req = requests.post(url=POST_TWEET_URL, data=request_data, auth=oauth)
        complete = req.json()['id']
        return complete

    def check_status(self):
        '''
        Checks video processing status
        '''
        if self.processing_info is None:
            return

        state = self.processing_info['state']
        print('Media processing status is %s ' % state)

        if state == 'succeeded':
            return

        elif state == 'failed':
            raise ValueError("Upload failed")

        else:

            check_after_secs = self.processing_info['check_after_secs']

            print('Checking after %s seconds' % str(check_after_secs))
            time.sleep(check_after_secs)

            print('STATUS')

            request_params = {
                'command': 'STATUS',
                'media_id': self.media_id
            }

            req = requests.get(url=MEDIA_ENDPOINT_URL,
                               params=request_params, auth=oauth)

            self.processing_info = req.json().get('processing_info', None)
            self.check_status()
