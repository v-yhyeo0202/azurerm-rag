import os
import subprocess
import yaml

with open('config.yml', 'r') as f:
    dictConfig = yaml.load(f, Loader = yaml.FullLoader)

def getBSameAzurermCommit():
    with open(os.path.join(dictConfig['path']['repository'], dictConfig['path']['data'], 'azurermCommit.txt'), 'r') as f:
        extractCommit = f.read().strip()

    currentCommit = subprocess.run(
        ['git', '-C', os.path.join(dictConfig['path']['repository'], 'terraform-provider-azurerm'), 'rev-parse', 'HEAD'],
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        text = True
    ).stdout.strip()

    print(f'AzureRM commit during chunk line extraction: {extractCommit}')
    print(f'AzureRM commit currently: {currentCommit}')

    return extractCommit == currentCommit
