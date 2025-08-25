
import requests
import random
from record_process import record2text
from entry_process import extract_texts
from configs import paraphrased_subsection

# from funchub.func_impl.uniprot.record_process import record2text
# from utils.configs import paraphrased_subsection

def web_query_uniprot(id):
    with requests.Session() as uniprot_api: # 先实例化一个对象
        results = uniprot_api.post(f'https://rest.uniprot.org/uniprotkb/{id}.json')
        results = results.json()
        return results

def get_record(id, subsection):
    data_dict = web_query_uniprot(id)
    records = extract_texts(data_dict)
    for record in records:
        if record[3] == subsection:
            return record

def uniprot_query(record, answers_template, paragraph2sentence, paraphrase):
    sequence_name, aa_length, section, subsection, _, raw_text, note = record
    # get answer
    text, raw_text_list = record2text(record, answers_template)
    if len(raw_text_list) == 0:
        raw_text_list = [text]
    if isinstance(text, list):
        idx = random.choice(range(len(text)))
        text = text[idx]
        raw_text_list = raw_text_list[idx]

    if subsection in paraphrased_subsection and text == raw_text:
        try:
            if text in paragraph2sentence[subsection]:
                sentences = paragraph2sentence[subsection][text]
            else:
                sentences = [text]
            sentence = random.choice(sentences)
            text = random.choice(paraphrase[subsection][sentence]+len(paraphrase[subsection][sentence])*[sentence])# half is original, half is paraphrased
        except:
            print(subsection)
            print(text)
    return text, raw_text_list