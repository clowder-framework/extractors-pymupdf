# extractors-pymupdf
Clowder extractor for PyMuPDF
Extractor takes pdf file as input and outputs json and csv files with textual contents of the pdf file.

## Instructions to run the extractor
- Activate the virtual environment
- Install dependencies: `pip install -r requirements.txt`
- Run the extractor: `python extractor.py`

## Build extractor image

- Run `docker build . -t hub.ncsa.illinois.edu/clowder/extractors-pymupdf:<version>` to build docker image
- If you ran into error `[Errno 28] No space left on device:`, try below:
    - Free more spaces by running `docker system prune --all` 
    - Increase the Disk image size. You can find the configuration in Docker Desktop

## Publish Image to Private NCSA repo
- Login first: `docker login hub.ncsa.illinois.edu`
- Run `docker image push hub.ncsa.illinois.edu/clowder/extractors-pymupdf:<version>`

## Deployment
- Please refer to Clowder instructions
- Current deployment `hub.ncsa.illinois.edu/clowder/extractors-pymupdf:0.2.0.0`
