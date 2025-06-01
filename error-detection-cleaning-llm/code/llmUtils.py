import pandas as pd
import ollamaModels as ollamaMod
import openAIModels as openAiMod


def getClient(llm_package,api_key,base_url):    
    if llm_package == "ollama":
        client = ollamaMod.getClient(base_url)
    elif llm_package == "openai":
        client = openAiMod.getClient(api_key,base_url)
    else:
        print("no llm package registered, no matching Client found")
        client = None
    return client

def askModel(llm_package,client,promptStr,modelname=None):  
    if llm_package == "ollama":
        resStr = ollamaMod.askLLM(promptStr,client,modelname)
    elif llm_package == "openai":
        resStr = openAiMod.askLLM(promptStr,client,modelname)
    elif llm_package == "huggingFace":
        resStr = openAiMod.askLLM(promptStr,client,modelname)
    else:
        print("no llm package registered, no matching Client found")
        resStr = None
    return resStr

def createResDf(list_of_tuples, colnames):
    dfAll = pd.DataFrame(list_of_tuples,
                    columns=colnames)
    return dfAll