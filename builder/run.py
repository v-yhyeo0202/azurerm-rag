import chromadb
import os
import readchar
import sentence_transformers
import sys
import yaml

import utility

with open('config.yml', 'r') as f:
    dictConfig = yaml.load(f, Loader = yaml.FullLoader)

if not utility.getBSameAzurermCommit():
    sys.exit('Commits are different, check out AzureRM repository to commit during chunk line extraction or run chunk line extraction again')

capitalizedModelName = f"{dictConfig['model'][0].upper()}{dictConfig['model'][1:]}"
client = chromadb.PersistentClient(os.path.join(dictConfig['path']['repository'], dictConfig['path']['database']))
modelId = dictConfig['modelInfo'][dictConfig['model']]['id']
model = sentence_transformers.SentenceTransformer(modelId, trust_remote_code = True, token = os.environ['HUGGINGFACE_TOKEN'])

listCollectionName = ['schema', 'property', 'method', 'config', 'file']
listCollectionName = [f'{i}_model{capitalizedModelName}' for i in listCollectionName]
listShortCollectionName = ['Schema', 'Property', 'Method', 'Config', 'File']

while True:
    print('\nPress number to select collection to query or `q` to quit\n')

    for i, shortCollectionName in enumerate(listShortCollectionName):
        print(f'[{i + 1}] {shortCollectionName}')

    pressedKey = readchar.readkey()

    if pressedKey == "q":
        print('\nQuitting')

        break
    elif not pressedKey.isdigit():
        print('\nNumber is not pressed, please try again')

        continue

    index = int(pressedKey) - 1
    collection = client.get_collection(listCollectionName[index])

    while True:
        query = input(f'\nEnter query to search from {listShortCollectionName[index].lower()} collection or `q` to stop\n')

        if query == "q":

            break

        embedding = model.encode(query)
        dictResult = collection.query([embedding], n_results = dictConfig['nResult'])
        print()

        for dictMetadata in dictResult['metadatas'][0]: # type: ignore
            startLine = f", {dictMetadata['startLine']}" if 'startLine' in dictMetadata else ''
            endLine = f", {dictMetadata['endLine']}" if 'endLine' in dictMetadata else ''
            print(f"{dictMetadata['path'].removeprefix(os.path.join(dictConfig['path']['repository'], 'terraform-provider-azurerm', ''))}{startLine}{endLine}") # type: ignore
