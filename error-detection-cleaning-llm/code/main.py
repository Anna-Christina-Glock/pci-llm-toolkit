import os
import numpy as np
from ollama import Client
import pandas as pd
import re

from llmUtils import createResDf,askModel,getClient
import json
from pathlib import Path
from openai import OpenAI
from prompt import initPromptDict, parseAnswer

import threading

def askModelSaveAnswer(llm_package,client,promptStr,modelname,promtId,modelConfigName,index,resLi,row,colNameMatchingDict=None,promptVal=None):
        resStr = askModel(llm_package,client,promptStr,modelname)
        #print(resStr)
        #print(f'  index: {promtId}')
        if colNameMatchingDict is None:
            if usePolData:            
                origDict={'id':index,'Strasse_orig':row['Strasse'], 'Hausnummer_orig':row['Hausnummer'], 'Stiege_orig':row['Stiege'], 
                        'Türnummer_orig':row['Türnummer'], 'Postleitzahl_orig':row['Postleitzahl'], 'Ort_orig':row['Ort'],
                        'errCol':row['errCol'],'errRule':row['errRule'],
                        'ModelId':modelConfigName}
            else:
                origDict={'id':index,'Strasse_orig':row['Strasse'], 'Hausnummer_orig':row['Hausnummer'], 'Stiege_orig':row['Stiege'], 
                        'Türnummer_orig':row['Türnummer'], 'Postleitzahl_orig':row['Postleitzahl'], 'Ort_orig':row['Ort'],'Regel_orig':row['Regel'],
                        'ModelId':modelConfigName}
        else:
            origDict=dict()        
            for key, value in colNameMatchingDict.items():
                origDict[f'{value}_orig'] = None if pd.isna(row[key]) else row[key]

        resLi.append(dict(parseAnswer(resStr,promptVal,index), **origDict))
        
# any config
config_folder = Path("config")
parameter_config_filename = config_folder/"parameter.json"
with open(parameter_config_filename) as param_file:
    parameter_config = json.load(param_file)

modelConfigName = parameter_config["modelConfigName"]
whichColMatchDict = parameter_config["whichColMatchDict"]

colNameMatchingDict = dict
if whichColMatchDict == 'postDataWithPers':
    colNameMatchingDict = {
        "Email": "Email",
        "Vorname": "Vorname",
        "Nachname": "Nachname",
        "PLZ": "Postleitzahl",
        "Ort": "Ort",
        "Strasse": "Strasse",
        "Hausnummer": "Hausnummer",
        "Stiege": "Stiege",
        "Tuernummer": "Türnummer",
        "Laendervorwahl": "LVorwahl",
        "Vorwahl": "Vorwahl",
        "Telefonnummer": "TelNr",
        "Land": "Land",
        "Geburtsdatum": "Geburtsdatum"
    }
elif whichColMatchDict == 'genDataWithPers':
    colNameMatchingDict = {
        "email": "Email",
        "vorname": "Vorname",
        "nachname": "Nachname",
        "plz": "Postleitzahl",
        "ort": "Ort",
        "straße": "Strasse",
        "hnr": "Hausnummer",
        "stiege": "Stiege",
        "tnr": "Türnummer",
        "landVorwahl": "LVorwahl",
        "vorwahl": "Vorwahl",
        "telNr": "TelNr",
        "land": "Land",
        "gebDat": "Geburtsdatum"
    }


# load llm connection config
connection_config_filename = config_folder/"connection.json"
with open(connection_config_filename) as config_file:
    llm_connection_config = json.load(config_file)

paramInitKey = parameter_config["location"]
llm_package=llm_connection_config[modelConfigName]["llm-package"]
api_key=llm_connection_config[modelConfigName]["api_key"]
base_url=llm_connection_config[modelConfigName]["base_url"]
modelname=llm_connection_config[modelConfigName]["modelname"]

data_folder = Path(parameter_config[paramInitKey]["Paths"]["Data"])
prompt_folder = Path(parameter_config[paramInitKey]["Paths"]["Prompt"])
connection_prompt_filename = prompt_folder/"prompt.json"
with open(connection_prompt_filename, encoding='utf-8') as config_file:
    prompt_connection_config = json.load(config_file)

promptDict=initPromptDict(prompt_connection_config,colNameMatchingDict)

promptIdLi = ['p4']

# Connection to LLM
print('Connect to Client')
client = getClient(llm_package,api_key,base_url)

print('Read Data from File')
usePolData = True
fileIdxArr = parameter_config[paramInitKey]["File"]["Input"]
for fileIdx in fileIdxArr:
    inputFileParam = parameter_config["Files"][fileIdx]

    file_path = Path(data_folder/inputFileParam['name'])
    if not file_path.exists():
        print(f"File does not exist: {file_path}")
        continue

    csvDf = pd.read_csv(data_folder/inputFileParam['name'],
                        encoding=(None if inputFileParam['encoding'] in "None" else inputFileParam['encoding']),
                        delimiter=(None if inputFileParam['delimiter'] in "None" else inputFileParam['delimiter']))
    print('Start Reading')
    isHeader = True
    modeVal = 'w'
    modeVal_Res = 'w'
    idxLi = []
    strLi = []
    hnLi = []
    stLi = []
    tnLi = []
    plzLi = []
    ortLi = []
    prLi = []
    repLi = []
    resLi = []
    threads = [None] * 52
    i = 0

    result_folder = Path(parameter_config[paramInitKey]["Paths"]["Result"])
    resFileSuff = parameter_config["Files"][fileIdx]["OutputSuffix"]


    for index, row in csvDf.iterrows():
        print('##################################')
        print(f'row: {index}')
        for promtId in promptIdLi:
            promptVal = promptDict[promtId]
            promptVal.setValues(row)
            promptStr = promptVal.getPrompt()
            threads[i] = threading.Thread(target=askModelSaveAnswer, 
                    args=(llm_package,client,promptStr,modelname,promtId,modelConfigName,index,resLi,row,colNameMatchingDict,promptVal))
            threads[i].start()
        
        i=i+1
        if (index % 50) == 1 and index > 1:
            for j in range(len(threads)):
                if threads[j] is None:
                    break
                threads[j].join()
            dfAll = pd.DataFrame(resLi)
            dfAll = dfAll.assign(modelname=modelname)
            dfAll.to_csv(result_folder/f'resDf_all_pol_{resFileSuff}.csv', mode=modeVal,header=isHeader)
            df = dfAll[dfAll.columns.difference(['Prompt','PromptId'])]
            df = df.assign(modelname=modelname)
            df.to_csv(result_folder/f'resDf_addOnly_pol_{resFileSuff}.csv', mode=modeVal,header=isHeader)
            resLi = []
            isHeader = False
            modeVal = 'a'    
            threads = [None] * len(threads)
            i=0
            
    for j in range(len(threads)):
        if threads[j] is None or i == 0:
            break
        threads[j].join()

    dfAll = pd.DataFrame(resLi)

    print(dfAll)
    fileName = f'resDf_all_pol_{resFileSuff}.csv'
    dfAll = dfAll.assign(modelname=modelname)
    dfAll.to_csv(result_folder/fileName, mode=modeVal,header=isHeader)
    df = dfAll[dfAll.columns.difference(['Prompt','PromptId'])]

    print(df)
    fileName = f'resDf_addOnly_pol_{resFileSuff}.csv'
    df = df.assign(modelname=modelname)
    df.to_csv(result_folder/fileName, mode=modeVal,header=isHeader)


