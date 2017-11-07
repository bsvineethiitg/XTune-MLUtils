def gaussian_feature_importances(df, missing_value=-1, skip_columns=['id','target']):
    '''
    If missing_value is provided then fields having -1 are neglected while generating feature importances.
    Assuming binary target. 
    df should have target column.
    skip columns from features can be provided.
    
    Remember Stat Mech course of Prof Nandy?
    '''
    
    cols = df.columns
    results = []
    
    for i in cols:
        if i in skip_columns:
            continue
        
        std0 = df[(df[i]!=missing_value) & (df['target']==0)][i].std()
        mean0 = df[(df[i]!=missing_value) & (df['target']==0)][i].mean()
        std1 = df[(df[i]!=missing_value) & (df['target']==1)][i].std()
        mean1 = df[(df[i]!=missing_value) & (df['target']==1)][i].mean()
        diff_mean = abs(mean1-mean0)
        diff_std = abs(std1-std0)
        try:
            significance_measure = diff_mean/diff_std
        except:
            significance_measure = None
        
        results.append([i, mean0, std0, mean1, std1, diff_mean, diff_std, significance_measure])
        
    results = pd.DataFrame(results)
    results.columns = 'col,mean0,std0,mean1,std1,diff_mean,diff_std,significance_measure'.split(',')
    
    return results.sort_values(by=['significance_measure', 'diff_mean'], ascending=False, kind='mergesort', na_position='first')
    
    
''' create feature interactions pairwise on train, and use those decided newfeature pickups for test using custom_ops'''
def create_pairwise_feature_interactions(df, custom_ops=[], columns=None, type='multiplicative', skip_cols=[]):
    ''' 
    Checks the statistical significance of new multiplicative feature combinations from the columns set given.
    If no columns are specified, then all combinations of the columns excluding the id and target fields are considered.
    id fields is considered to be some non feature column
    target fields is considered to be the GT column
    Specify more skip columns by skip_columns
    type: 'multiplicative' or 'additive' or 'both'
    
    custom_ops: you can specify a list of strings that ask for certain particular custom interaction features to
    be added. Example: newfeature-F1-F2_add, newfeature_F1-F2_mul will create F1+F2 feature, F1*F2 respectively.
    
    '''
    
    newdf = pd.DataFrame()
    
    if 'target' in df.columns:
        newdf['target'] = df['target']
    
    if len(custom_ops)!=0:
        for i in custom_ops:
            
            if i.split('|')[0] == 'newfeature':
                operation = i.split('|')[-1]
                f1 = i.split('|')[1]
                f2 = i.split('|')[2]

                if operation == 'add':
                    newdf[i] = df[f1] + df[f2]
                elif operation == 'mul':
                    newdf[i] = df[f1] * df[f2]
            else:
                newdf[i] = df[i]
        
        if 'target' in newdf.columns:
            return newdf, feature_importances(newdf)    
        else: 
            return newdf
            
    
    if columns is None:
        givencolumns = df.columns
        columns = []
        for i in givencolumns:
            if i!='id' and i!='target' and i not in skip_cols:
                columns.append(i)
    
    # keep the original columns intact
    for i in columns:
        newdf[i] = df[i]
    
    counter1 = 0
    for i in range(len(columns)):
        percent = (counter1*100)/float(len(columns))
        if int(percent) % 2 == 0 and int(percent)!=0:
            print('Progress: ', percent, ' %', end='')
        
        if i == len(columns) -1 :
            break
        for j in range(i+1, len(columns)):
            
            if type=='multiplicative' or type=='both':
                newdf['newfeature|'+columns[i]+'|'+columns[j]+'|mul'] = df[columns[i]] * df[columns[j]]
                
            if type=='additive' or type=='both':
                newdf['newfeature|'+columns[i]+'|'+columns[j]+'|add'] = df[columns[i]] + df[columns[j]]
                
        counter1+=1
        
        
    if 'target' in newdf.columns:
        return newdf, feature_importances(newdf)    
    else:
        return newdf



import bcolz
def save_array(fname, arr):
    c=bcolz.carray(arr, rootdir=fname, mode='w')
    c.flush()


def load_array(fname):
    return bcolz.open(fname)[:]



# Criag Glastonbury 23rd on PB LB (0.5 logloss) did a preprocessing of normalizing the RGB histogram with
# Obvly it gave him great results than us (~1 logloss) :/
import cv2

def normalized(rgb):
    norm=np.zeros((rgb.shape[0], rgb.shape[1], 3),np.float32)
    b=rgb[:,:,0]
    g=rgb[:,:,1]
    r=rgb[:,:,2]
    norm[:,:,0]=cv2.equalizeHist(b)
    norm[:,:,1]=cv2.equalizeHist(g)
    norm[:,:,2]=cv2.equalizeHist(r)
    return norm

def get_im_cv2(path):
    img = cv2.imread(path,1)
    
    # For color historgram
    img_yuv = cv2.cvtColor(img, cv2.COLOR_BGR2YUV)

    # equalize the histogram of the Y channel
    img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])

    # convert the YUV image back to RGB format
    img_output = cv2.cvtColor(img_yuv, cv2.COLOR_YUV2BGR)
    
    # Sharpen
    output_3 = cv2.filter2D(img_output, -1, kernel_sharpen_3)
    
    # Reduce to manageable size
    resized = cv2.resize(output_3, (224, 224), interpolation = cv2.INTER_LINEAR)
    return resized


# Whenever using pretrained models, please be sure to do the necessary preprocessing on the inputs
# A lot of tutorials online for transfer learning miss this very important step. 
# Example for VGG 16 in Keras (it's got a readymade function, use it!):
from keras.applications.vgg16 import preprocess_input # Input preprocessing for VGG16 pretrained model