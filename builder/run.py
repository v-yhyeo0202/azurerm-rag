import chromadb
import os
import readchar
import sentence_transformers
import yaml

with open('config.yml', 'r') as f:
    dictConfig = yaml.load(f, Loader = yaml.FullLoader)

capitalizedModelName = f"{dictConfig['model'][0].upper()}{dictConfig['model'][1:]}"
client = chromadb.PersistentClient(dictConfig['path']['database'])
modelId = dictConfig['modelInfo'][dictConfig['model']]['id']
model = sentence_transformers.SentenceTransformer(modelId, trust_remote_code = True, token = os.environ['HUGGINGFACE_TOKEN'])

listCollectionName = ['method', 'config']
listCollectionName = [f'{i}_model{capitalizedModelName}' for i in listCollectionName]
listShortCollectionName = ['Method', 'Config']

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
            print(f"{dictMetadata['path'].removeprefix(os.path.join(dictConfig['path']['home'], dictConfig['path']['azurerm']))}, {dictMetadata['startLine']}, {dictMetadata['endLine']}") # type: ignore
