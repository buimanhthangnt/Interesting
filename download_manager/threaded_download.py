from __future__ import division, print_function
import requests
import threading
import time
import sys
import numpy as np
from argparse import ArgumentParser


parser = ArgumentParser()
parser.add_argument('-t', type=int, help='Number of threads', default=8)
parser.add_argument('-url', type=str, help='File url to download')
args = parser.parse_args()
num_threads = args.t
url = args.url


class DownloadManager:
    def __init__(self, num_threads):
        self.num_threads = max(1, min(num_threads, 16))
        self.status = [0 for i in range(num_threads)]
        self.current_time = time.time()
        self.update_interval = 1


    def partly_download(self, start, end, url, filename, index):
        fn = open(filename, 'r+b')
        headers = {'Range': 'bytes=%d-%d' % (start, end)}
        response = requests.get(url, headers=headers, stream=True)
        total_length = response.headers.get('content-length')
        if total_length != None:
            total_length = int(total_length)
            downloaded = 0
            chunk_size = 2048
            for idx, data in enumerate(response.iter_content(chunk_size=chunk_size)):
                fn.seek(start + idx * chunk_size)
                var = fn.tell()
                fn.write(data)
                downloaded += len(data)
                self.status[index] = int(50 * downloaded / total_length)
                now = time.time()
                if now - self.current_time > self.update_interval or self.status[index] == 50:
                    self.current_time = now
                    mean_current = int(np.mean(self.status))
                    sys.stdout.write("\r[%s%s]" % ('#' * mean_current, ' ' * (50-mean_current)) )    
                    sys.stdout.flush()


    def normal_download(self, url, filename):
        req = requests.get(url)
        with open(filename, 'wb') as fn:
            fn.write(req.content)


    def download(self, url):
        req = requests.head(url)
        filename = url.split('/')[-1].split('?')[0]
        print("Downloading %s file using %d threads..." % (filename, self.num_threads))

        if '.' not in filename:
            print("No file extension found. You can manually add to the filename")
            print("Common extensions are .mp3 .mp4 .jpg .png .pdf .docx ...")

        if 'Accept-Ranges' not in list(req.headers.keys()):
            print("Server doesn't support download partially. Normal download is used")
            self.normal_download(url, filename)
            return
        try:
            filesize = int(req.headers['content-length'])
        except:
            print("Invalid url. Please check again!")

        part = int(filesize / self.num_threads)
        fn = open(filename, "wb")
        fn.close()

        for i in range(self.num_threads):
            start = part * i
            end = start + part
            thr = threading.Thread(target=self.partly_download, kwargs={
                'start': start, 'end': end, 'url': url, 'filename': filename, 'index': i})
            thr.setDaemon(True)
            thr.start()

        main_thread = threading.current_thread()
        for thr in threading.enumerate():
            if thr is main_thread: continue
            thr.join()
        
        print("\nDownloaded successfully file: %s" % filename)


if __name__ == '__main__':
    prev = time.time()
    downloader = DownloadManager(num_threads)
    downloader.download(url)
    print("Finished in %f seconds." % float(time.time() - prev))
