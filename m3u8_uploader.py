import os
import requests
from tqdm import tqdm
import subprocess
import argparse
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type


# Define a retry decorator for requests
@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10),
       retry=retry_if_exception_type(requests.exceptions.RequestException))
def download_segment(segment_url, segment_filename):
    response = requests.get(segment_url, stream=True, timeout=10)
    with open(segment_filename, 'wb') as segment_file:
        for chunk in response.iter_content(chunk_size=8192):
            segment_file.write(chunk)


def download_m3u8(m3u8_url, download_folder):
    print('Starting upload: ')
    response = requests.get(m3u8_url)
    m3u8_content = response.text

    # Parse the m3u8 file to get all segment URLs
    base_url = m3u8_url.rsplit('/', 1)[0]
    segment_urls = []
    for line in m3u8_content.splitlines():
        if line and not line.startswith('#'):
            segment_urls.append(f"{base_url}/{line}")

    # Download all segments with a progress bar
    segment_files = []
    for i, segment_url in enumerate(tqdm(segment_urls, desc="Downloading segments", unit="segment")):
        segment_filename = os.path.join(download_folder, f'segment_{i}.ts')
        download_segment(segment_url, segment_filename)
        segment_files.append(segment_filename)

    return segment_files


def combine_segments(segment_files, output_file):
    print('Combining uploaded files: ')
    with open('file_list.txt', 'w') as f:
        for segment in segment_files:
            f.write(f"file '{segment}'\n")

    # Run ffmpeg to combine segments
    ffmpeg_command = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', 'file_list.txt', '-c', 'copy', output_file]
    result = subprocess.run(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    if result.returncode != 0:
        raise("FFmpeg error:", result.stderr)
    else:
        pass


def main():
    parser = argparse.ArgumentParser(description="Download and combine M3U8 video segments into a single file.")
    parser.add_argument('url', help='The URL of the M3U8 playlist')
    parser.add_argument('file', help='The name of the output video file')
    args = parser.parse_args()

    m3u8_url = args.url
    output_folder = './downloaded_files/'
    output_file = output_folder + args.file + '.mp4'
    download_folder = './downloaded_segments'

    os.makedirs(download_folder, exist_ok=True)
    os.makedirs(output_folder, exist_ok=True)
    segment_files = download_m3u8(m3u8_url, download_folder)
    combine_segments(segment_files, output_file)

    for segment_file in segment_files:
        os.remove(segment_file)
    os.remove('file_list.txt')

    print(f'Video has been saved as {output_file}')


if __name__ == "__main__":
    main()
