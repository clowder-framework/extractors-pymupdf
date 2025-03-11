import time
import logging
import os
import pandas as pd
import fitz  # PyMuPDF
import os
import time
import json
import spacy
import scispacy  # (optional: this import ensures SciSpaCy is installed)

from pyclowder.extractors import Extractor
import pyclowder.files

# create log object with current module name
log = logging.getLogger(__name__)


class PyMuPDFExtractor(Extractor):
    def __init__(self):
        Extractor.__init__(self)

        # add any additional arguments to parser
        # self.parser.add_argument('--max', '-m', type=int, nargs='?', default=-1,
        #                          help='maximum number (default=-1)')

        # parse command line and load default logging configuration
        self.setup()

        # setup logging for the extractor
        logging.getLogger('pyclowder').setLevel(logging.INFO)
        logging.getLogger('__main__').setLevel(logging.INFO)

        # Load the SciSpaCy model
        self.nlp = spacy.load("en_core_sci_sm")


    def extract_sections(self, page):
        """
        Extract words from the page, build a combined text string, and use the SciSpaCy
        model to segment the text into sentences.

        This function uses page.get_text("words") to retrieve all words (with coordinates),
        then concatenates them (in reading order) inserting spaces between words.
        Finally, it returns a list of sentence texts extracted by the SciSpaCy sentence tokenizer.
        """
        # Each word is a tuple: (x0, y0, x1, y1, word, block_no, line_no, word_no)
        words = page.get_text("words")
        # Sort words in reading order.
        words.sort(key=lambda w: (w[5], w[6], w[7]))

        # Build a combined text string and record each word's offset.
        combined_text_parts = []
        current_offset = 0
        word_offsets = []  # List of tuples (start, end) for each word.

        for w in words:
            word_text = w[4]
            combined_text_parts.append(word_text)
            start = current_offset
            end = start + len(word_text)
            word_offsets.append((start, end))
            # Assume a single space between words.
            current_offset = end + 1

        combined_text = " ".join(combined_text_parts)

        # Process the combined text with SciSpaCy.
        doc = self.nlp(combined_text)
        sentences = [sent.text.strip() for sent in doc.sents]
        return sentences



    def process_message(self, connector, host, secret_key, resource, parameters):
        # Process the file and upload the results
        # uncomment to see the resource
        # log.info(resource)
        # {'type': 'file', 'id': '6435b226e4b02b1506038ec5', 'intermediate_id': '6435b226e4b02b1506038ec5', 'name': 'N18-3011.pdf', 'file_ext': '.pdf', 'parent': {'type': 'dataset', 'id': '64344255e4b0a99d8062e6e0'}, 'local_paths': ['/tmp/tmp2hw6l5ra.pdf']}

        input_file = resource["local_paths"][0]
        input_file_id = resource['id']
        dataset_id = resource['parent'].get('id')
        input_filename = os.path.splitext(os.path.basename(resource["name"]))[0]
        input_file_ext = resource['file_ext']
        if input_file_ext == ".pdf":
            output_json_file = os.path.join(os.path.splitext(os.path.basename(input_filename))[0] + "-pymupdf" + ".json")
            output_json_filename = os.path.join(input_filename + "-pymupdf" + ".json")
            output_csv_file = os.path.join(os.path.splitext(os.path.basename(input_filename))[0] + "-pymupdf" + ".csv")
            output_csv_filename = os.path.join(input_filename + "-pymupdf" + ".csv")
        else:
            raise ValueError("Input file is not a PDF")
        # These process messages will appear in the Clowder UI under Extractions.
        connector.message_process(resource, "Loading contents of file for pymupdf extraction...")
        
        # -------------------- Main Processing Loop --------------------
        # We'll save two outputs for each PDF:
        #   1. The annotated PDF (without black boxes for sentences).
        #   2. A JSON file containing only the list of extracted sentences (per page).
        try:
            start_time = time.time()
            doc = fitz.open(input_file)
            # Create a new document for the annotated PDF.
            # new_doc = fitz.open()
            # This dictionary will hold the sentences extracted per page.
            sentences_output = {"pages": []}
            all_sentences = []

            for page_number in range(len(doc)):
                page = doc.load_page(page_number)
                # Create a new page in the new document with the same dimensions.
                # new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
                # new_page.show_pdf_page(new_page.rect, doc, page_number)  # Copy original content.

                # Use PyMuPDF's text extraction; use OCR if needed.
                # if not page.get_text():
                #     tp = page.get_textpage_ocr(dpi=300, full=True)
                # else:
                #     tp = page.get_textpage()
                # (We still extract the text dictionary if needed for further processing.)
                # text_dict = tp.extractDICT()

                # Extract sentences using our SciSpaCy helper.
                sentences = self.extract_sections(page)
                for sentence in sentences:
                    all_sentences.append({"file": os.path.basename(input_file), "section": "", "sentence": sentence, "coordinates": ""})
                # Save the sentences (without coordinates) for this page.
                sentences_output["pages"].append({"page_number": page_number, "sentences": sentences})
                # (Optional) If you want to visualize, you can draw bounding boxes for other elements,
                # but here we skip drawing the sentence boxes to avoid clutter.
                # For example, you might still draw text spans in red if desired:
                # for block in text_dict.get("blocks", []):
                #     if "lines" in block:
                #         for line in block["lines"]:
                #             for span in line["spans"]:
                #                 bbox = span["bbox"]
                #                 # Draw text span boxes in red (you can comment this out if not needed)
                #                 new_page.draw_rect(bbox, color=(1, 0, 0), width=0.5)

                # # (Optional) Draw table bounding boxes if found.
                # tables = page.find_tables()
                # if tables:
                #     for table in tables:
                #         table_bbox = table.bbox
                #         new_page.draw_rect(table_bbox, color=(0.5, 0, 0), width=1.5)
                #         print(f"Table found in {pdf_file}, page {page_number}: {table_bbox}")
                # Save the annotated PDF in the output folder.
            
            # new_doc.save(output_pdf_file, garbage=4, deflate=True, clean=True)
            # new_doc.close()
            doc.close()

            # Save the JSON file containing only the extracted sentences.
            with open(output_json_file, "w", encoding="utf-8") as jf:
                json.dump(sentences_output, jf, ensure_ascii=False, indent=4)

             # convert sentences to csv
            sentences_df = pd.DataFrame(all_sentences, columns=['file', 'section', 'sentence', 'coordinates'])
            sentences_df = sentences_df.astype(str)
            sentences_df.to_csv(output_csv_file, index=False)

            end_time = time.time()
            processing_time = end_time - start_time
            log.info(f"Processed {input_filename} in {processing_time:.2f} seconds.")
            
            log.info("Output Json file generated : %s", output_json_file)
            connector.message_process(resource, "PyMuPDF extraction completed.")

            # clean existing duplicate
            files_in_dataset = pyclowder.datasets.get_file_list(connector, host, secret_key, dataset_id)
            for file in files_in_dataset:
                if file["filename"] == output_csv_filename or file["filename"] == output_json_filename:
                    url = '%sapi/files/%s?key=%s' % (host, file["id"], secret_key)
                    connector.delete(url, verify=connector.ssl_verify if connector else True)
            connector.message_process(resource, "Check for duplicate files...")

            # upload to clowder
            connector.message_process(resource, "Uploading output files to Clowder...")
            json_fileid = pyclowder.files.upload_to_dataset(connector, host, secret_key, dataset_id, output_json_filename)
            csv_fileid = pyclowder.files.upload_to_dataset(connector, host, secret_key, dataset_id, output_csv_filename)
            # upload metadata to dataset
            extracted_files = [
                {"file_id": input_file_id, "filename": input_filename, "description": "Input pdf file"},
                {"file_id": json_fileid, "filename": output_json_filename, "description": "PyMuPDF JSON output file"},
                {"file_id": csv_fileid, "filename": output_csv_filename, "description": "PyMuPDF CSV output file"},
            ]
            content = {"extractor": "pymupdf-extractor", "extracted_files": extracted_files}
            context = "http://clowder.ncsa.illinois.edu/contexts/metadata.jsonld"
            #created_at = datetime.now().strftime("%a %d %B %H:%M:%S UTC %Y")
            user_id = "http://clowder.ncsa.illinois.edu/api/users"  # TODO: can update user id in config
            agent = {"@type": "user", "user_id": user_id}
            metadata = {"@context": [context], "agent": agent, "content": content}
            pyclowder.datasets.upload_metadata(connector, host, secret_key, dataset_id, metadata)
        except Exception as e:
            log.error(f"PyMuPDF Extractor Error processing file {input_filename} : {e}")
            connector.message_process(resource, f"PyMuPDF Extractor Error processing file {input_filename} : {e}")


if __name__ == "__main__":
    # uncomment for testing
    # input_file = "data/2020.acl-main.207.pdf"
    # output_pdf_file = os.path.join(os.path.splitext(os.path.basename(input_file))[0] + "-pymupdf" + ".pdf")
    # output_json_file = os.path.join(os.path.splitext(os.path.basename(input_file))[0] + "-pymupdf" + ".json")
    # output_csv_file = os.path.join(os.path.splitext(os.path.basename(input_file))[0] + "-pymupdf" + ".csv")

    # extractor = PyMuPDFExtractor()
    # doc = fitz.open(input_file)
    # # This dictionary will hold the sentences extracted per page.
    # sentences_output = {"pages": []}
    # all_sentences = []

    # for page_number in range(len(doc)):
    #     page = doc.load_page(page_number)
    #     # Extract sentences using our SciSpaCy helper.
    #     sentences = extractor.extract_sections(page)
    #     # Save the sentences for this page.
    #     for sentence in sentences:
    #         all_sentences.append({"file": os.path.basename(input_file), "section": "", "sentence": sentence, "coordinates": ""})
    #     sentences_output["pages"].append({"page_number": page_number, "sentences": sentences})
    # doc.close() 
    # # Save the JSON file containing only the extracted sentences.
    # with open(output_json_file, "w", encoding="utf-8") as jf:
    #     json.dump(sentences_output, jf, ensure_ascii=False, indent=4)

    # # convert sentences to csv
    # sentences_df = pd.DataFrame(all_sentences, columns=['file', 'section', 'sentence', 'coordinates'])
    # sentences_df = sentences_df.astype(str)
    # sentences_df.to_csv(output_csv_file, index=False)

    extractor = PyMuPDFExtractor()
    extractor.start()
