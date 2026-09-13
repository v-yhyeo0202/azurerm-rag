import chromadb
import itertools
import numpy as np
import os
import pandas as pd
import pathlib
import sentence_transformers
import shutil
import sys
import uuid
import yaml

import utility

with open('config.yml', 'r') as f:
    dictConfig = yaml.load(f, Loader = yaml.FullLoader)

def getUuid():
    listUuid = [uuid.uuid4().hex for _ in range(dictConfig['batch'])]

    return listUuid

def getBWithinContextWindow(model: sentence_transformers.SentenceTransformer, chunk: str):
    bWithinContextWindow = model.max_seq_length is not None and len(model.tokenizer.encode(chunk)) <= model.max_seq_length

    return bWithinContextWindow

def encodePartOfFile(model: sentence_transformers.SentenceTransformer, collection: chromadb.Collection, df: pd.DataFrame):
    listMetadata = []
    listChunk = []

    for i in range(len(df.index)):
        if (len(listChunk) % dictConfig['batch'] == 0 and len(listChunk) > 0) or i == len(df.index) - 1:
            matEmbedding = model.encode(listChunk)
            collection.add([uuid.uuid4().hex for _ in range(dictConfig['batch'])], matEmbedding.tolist(), listMetadata)
            listMetadata.clear()
            listChunk.clear()

        with open(df.loc[i, 'path'], 'r') as f:
            chunk = ''.join(itertools.islice(f, df.loc[i, 'startLine'], df.loc[i, 'endLine']))

            if getBWithinContextWindow(model, chunk):
                chunkName = f" `{df.loc[i, 'chunkName']}`" if isinstance(df.loc[i, 'chunkName'], str) else ''
                print(f"Encoding {df.loc[i, 'chunkType']}{chunkName} `{df.loc[i, 'path']}`")

                listChunk.append(chunk)
                listMetadata.append(
                {
                    'path': df.loc[i, 'path'],
                    'startLine': int(df.loc[i, 'startLine']),
                    'endLine': int(df.loc[i, 'endLine'])
                })
            else:
                chunkName = f" `{df.loc[i, 'chunkName']}`" if isinstance(df.loc[i, 'chunkName'], str) else ''
                print(f"Fail to encode {df.loc[i, 'chunkType']}{chunkName} `{df.loc[i, 'path']}`")

    return

if not utility.getBSameAzurermCommit():
    sys.exit('Commits are different, check out AzureRM repository to commit during chunk line extraction or run chunk line extraction again')

modelId = dictConfig['modelInfo'][dictConfig['model']]['id']
model = sentence_transformers.SentenceTransformer(modelId, trust_remote_code = True, token = os.environ['HUGGINGFACE_TOKEN'])
databasePath = os.path.join(dictConfig['path']['repository'], dictConfig['path']['database'])

if dictConfig['bReset'] and  os.path.exists(databasePath):
    shutil.rmtree(databasePath)

client = chromadb.PersistentClient(databasePath)
capitalizedModelName = f"{dictConfig['model'][0].upper()}{dictConfig['model'][1:]}"
fileCollection = client.create_collection(f'file_model{capitalizedModelName}')
listMetadata = []
listChunk = []

dirPath = pathlib.Path(os.path.join(dictConfig['path']['repository'], 'terraform-provider-azurerm', 'internal'))
listPath = [str(path) for path in dirPath.rglob('*.go')]

for i, path in enumerate(listPath):
    if (len(listChunk) % dictConfig['batch'] == 0 and len(listChunk) > 0) or i == len(listPath) - 1:
        matEmbedding = model.encode(listChunk)
        fileCollection.add(getUuid(), matEmbedding.tolist(), listMetadata)
        listMetadata.clear()
        listChunk.clear()

    with open(path, 'r') as f:
        chunk = f.read()

        if getBWithinContextWindow(model, chunk):
            print(f'Encoding file `{path}`')
            listChunk.append(chunk)
            listMetadata.append(
            {
                'path': path
            })
        else:
            print(f'Fail to encode file `{path}`')

df = pd.read_csv(os.path.join(dictConfig['path']['repository'], dictConfig['path']['data'], 'chunkLine.csv'))
listChunkType = np.unique(df.loc[:, 'chunkType']).tolist()

for chunkType in listChunkType:
    collection = client.create_collection(f'{chunkType}_model{capitalizedModelName}')
    srBChunkType = df.loc[:, 'chunkType'] == chunkType
    encodePartOfFile(model, collection, df.loc[srBChunkType, :].reset_index())
