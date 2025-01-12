# %%
import re
import glob
import argparse
import datetime
import platform
import subprocess
import pandas as pd

from PyPDF2 import PdfReader
from getpass import getpass

# %%
def clear_terminal():
    if platform.system() == 'Windows':
        subprocess.run('cls', shell=True)
    elif platform.system() == 'Linux':
        subprocess.run('clear', shell=True)

clear_terminal()

# %%
parser = argparse.ArgumentParser(description='Script para processamento de fatura Santander')

parser.add_argument('--file', type=str, help='Nome do arquivo PDF')
parser.add_argument('--passwd', type=str, help='Senha do arquivo PDF')

args = parser.parse_args()

try:
    file = args.file or glob.glob('Fatura*.pdf')[0]
    document = PdfReader(file)
except:
    print('Nenhuma fatura encontrada')
    exit()
    
clear_terminal()

# %%
if document.is_encrypted:
    success = False
    
    while not success:
        password = getpass("Digite a senha para descriptografar o PDF: ")
        success = document.decrypt(password)
        
        if not success:
            clear_terminal()
            print("Falha ao descriptografar o PDF. Verifique a senha.")
            
    clear_terminal()

# %%
data = {}
owners = set()
current_owner = None

for page in document.pages[1:]:
    pattern = r'^[A-Z\s]+-\s\d{4}\s[A-Z]{4}\s[A-Z]{4}\s\d{4}'
    
    page = page.extract_text()
    lines = page.splitlines()
    
    for line in lines:
        content = line.replace('  ', ' ').strip()
        
        if len(content.split()) < 3:
            continue
        
        if re.match(pattern, content) or content.startswith('@'):
            formated = content.replace('@', '').split()[0].title()
            owner = formated.replace('Lilian', 'Cunhada').replace('Jessica', 'Fernanda')
            
            if owner not in owners:
                data[owner] = []
                owners.add(owner)

            current_owner = owner
            continue
            
        if current_owner:
            data[current_owner].append(content)

# %%
for owner in data:
    for line in data[owner][:]:
        if not line[0].isdigit() and not line[-1].isdigit():
            data[owner].remove(line)

        if line.startswith(('VALOR', '(', 'Saldo', 'COTAÇÃO ')) or 'PAGAMENTO DE FATURA ' in line:
            data[owner].remove(line)
            
        if len(line.split(maxsplit=1)[0]) == 1:
            line = line[2:]

# %%
dataset = {}

for owner in data:
    dataset[owner] = []
    
    for i, line in enumerate(data[owner]):
        if len(line.split()[0]) == 1:
            line = line[2:]
            
        if line.startswith('IOF'):
            line = f"{data[owner][i - 1].split()[0]} {line}"

        if line.count(',') > 1:
            line = line.rsplit(maxsplit=1)[0]
        
        if line[-1].isalpha():
            parts = line.rsplit(',', 1)
            line = f'{parts[0]},{parts[1][:2]}'
        
        date, line_parts = line.split(maxsplit=1)
        desc, value = line_parts.rsplit(maxsplit=1)
        
        dataset[owner].append([date, desc, value.replace('.', '')])

# %%
base_date = datetime.datetime.now().strftime('%b/%y')

dataframes = []

for owner in dataset:
    df = pd.DataFrame(dataset[owner], columns=['Data', 'Descricao', 'Valor'])
    
    df[owner] = df['Valor']
    df['Base'] = base_date
    df['_date'] = pd.to_datetime(df['Data'], format='%d/%m', errors='coerce')
    
    cols = ['Base', 'Data', 'Descricao', 'Valor', owner, '_date']
    
    df = df[cols].sort_values('_date')
    
    df.drop(columns='_date', inplace=True)
    
    dataframes.append(df)
    
df = pd.concat(dataframes, ignore_index=True)

# %%
df.to_csv('relatorio.csv', index=False)

# %%
print('Relatório gerado com sucesso!')


