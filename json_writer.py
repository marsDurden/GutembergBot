import pandas as pd

import os
from os.path import join

import json

folder = "data"
file_input = join(folder, "comitato_autogestione.xlsx")
file_output = join(folder, "matricole.json")

true_list = ['si', 'Si', 'sì', 'Sì']
false_list = ['no', 'No']

column_names = ['CognomeNome',
                'Cellulare',
                'Matricola',
                'Mail',
                'idTelegram',
                'corsoBase',
                'corsoBasso',
                'note']

def corsoEnc(r):
    if r['corsoBase']:
        if r['corsoBasso']:
            return ''
        else:
            return 'Y'
    else:
        return 'X'


def path_check(f):
    if os.path.exists(f):
        return
    else:
        raise FileExistsError("Input data are not available")


def parse_xlsx(f):
    try:
        df = pd.read_excel(f, header=0, true_values=true_list, false_values=false_list, skiprows=[0,1], names=column_names)
    except:
        df = pd.read_excel(f, header=0, skiprows=[0,1], names=column_names)
        df['corsoBase'] = df['corsoBase'].apply(lambda x: True if x in true_list else False)
        df['corsoBasso'] = df['corsoBasso'].apply(lambda x: True if x in true_list else False)
    print(df.head())
    return df


def main():
    path_check(file_input)
    dataset = parse_xlsx(file_input)

    preformatted = {str(int(row['idTelegram'])) + corsoEnc(row): {
        'nome': row['CognomeNome'],
        'matricola': str(row['Matricola'])
        } for index, row in dataset.iterrows() if row['idTelegram'] == row['idTelegram']}

    preformatted['descrizione'] = "Questo è il file con le matricole e i nomi di chi chiude l'Aula Pollaio per la generazione automatica del file. Questo file è automaticamente generato dallo script json_writer.py. Validare il file sul sito https://jsonformatter.curiousconcept.com/ prima di mandarlo al bot."

    with open(file_output, 'w') as output_file:
        json.dump(preformatted, output_file, ensure_ascii=False, indent=4, sort_keys=True)


if __name__ == '__main__':
    main()
