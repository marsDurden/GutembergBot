import pandas as pd

import os
from os.path import join

import json

folder = "data"
file_input = join(folder, "comitato_autogestione.xlsx")
file_output = join(folder, "matricole.json")

true_list = ['si', 'Si', 'sì', 'Sì', 'SI', 'SÌ']
false_list = ['no', 'No', 'NO']

column_names = ['CognomeNome',
                'Cellulare',
                'Matricola',
                'Mail',
                'idTelegram',
                'corsoBase',
                'corsoBasso',
                'note']

def corsoEnc(r):
    """
    Codifica l'avere o meno fatto i due corsi sulla sicurezza attraverso una stringa
    
    Parameters
    ---------
    r : Dataframe row (or dict)
        Dizionario (o riga di un DataFrame) che contiene le informazioni sui corsi
        
    Returns
    -------
    str
        Codice: '' se ha sostenuto entrambi i corsi, 'Y' se ha sostenuto solo il base, 'X' se nessuno dei due
        [ Momentaneamente possono chiudere l'aula anche quelli che hanno sostenuto solo il primo corso ]
    """
    if r['corsoBase']:
        if r['corsoBasso']:
            return ''
        else:
            #return 'Y'
            return ''
    else:
        return 'X'


def path_check(f):
    """
    Controlla esistenza dei dati di input
    
    Parameters
    ---------
    f : str
        Nome del file di input (con path relativo)
        
    """
    try:
        os.makedirs(folder, exist_ok=True)
    except TypeError:
        try:
            os.makedirs(folder)
        except FileExistsError:
            pass
    
    if os.path.exists(f):
        return
    else:
        raise FileExistsError("Input data are not available")


def parse_xlsx(f):
    """
    Legge il file con i dati di input e restituisce un dataframe Pandas
    
    Parameters
    ---------
    f : str
        Nome del file di input (con path relativo)
        
    Returns
    -------
    DataFrame
        Il contenuto del file
    """
    try:
        df = pd.read_excel(f, header=0, true_values=true_list, false_values=false_list, skiprows=[0,1], names=column_names, sheet_name='Chiusure')
    except:
        df = pd.read_excel(f, header=0, skiprows=[0,1], names=column_names, sheet_name='Chiusure')
        df['corsoBase'] = df['corsoBase'].apply(lambda x: True if x in true_list else False)
        df['corsoBasso'] = df['corsoBasso'].apply(lambda x: True if x in true_list else False)
    df['CognomeNome'] = df['CognomeNome'].str.strip()
    return df


def main():
    path_check(file_input)
    dataset = parse_xlsx(file_input)

    preformatted = {str(int(row['idTelegram'])) + corsoEnc(row): {
        'nome': row['CognomeNome'],
        'matricola': str(row['Matricola']).strip()
        } for index, row in dataset.iterrows() if row['idTelegram'] == row['idTelegram']}

    preformatted['descrizione'] = "Questo è il file con le matricole e i nomi di chi chiude l'Aula Pollaio per la generazione automatica del file. Questo file è automaticamente generato dallo script json_writer.py. Validare il file sul sito https://jsonformatter.curiousconcept.com/ prima di mandarlo al bot."

    with open(file_output, 'w') as output_file:
        json.dump(preformatted, output_file, ensure_ascii=False, indent=4, sort_keys=True)


if __name__ == '__main__':
    main()
