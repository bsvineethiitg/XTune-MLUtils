'''
Created on Nov 18, 2017

@author: Vineeth_Bhaskara
'''
from __future__ import print_function
import numpy as np
import pandas as pd
import pickle
import os
import sys
import bcolz
import cv2
import hashlib
import random, math
from xtune import *
from sklearn.metrics import roc_auc_score, log_loss
from sklearn.metrics import confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import itertools


def plot_confusion_matrix(y_true, y_pred, 
                          target_names_map,
                          cutoff=None,
                          title='Confusion matrix',
                          cmap=None,
                          normalize=False,
                          plt_show=True):
    """
    No more confusion in plotting the SKLearn's bland Confusion Matrix!
    Arguments
    ---------
    y_true : array, shape = [n_samples]
    Ground truth (correct) target values.
    y_pred : array, shape = [n_samples]
    Estimated targets as returned by a classifier.
    target_names_map: given classification classes mapped to
                  the class names, for example: {0:'survive', 1:'death'}
    
    cutoff:     if cutoff is None, then y_pred is expected to be prediction classes
                but not probabilities. Specify a cutoff then you can send in probabs for y_pred. 
                (y_true must always be class labels though.) Example: 0.5 this means that
                if y_pred for class 1 is > 0.5 then it will be classified as class 1. Valid for Binary classes. 
    title:        the text to display at the top of the matrix
    cmap:         the gradient of the values displayed from matplotlib.pyplot.cm
                  see http://matplotlib.org/examples/color/colormaps_reference.html
                  plt.get_cmap('jet') or plt.cm.Blues
    normalize:    If False, plot the raw numbers
                  If True, plot the proportions
    Usage
    -----
    p=0.1
    plot_confusion_matrix(df_test['label'].values.tolist(), val_pred, 
                              target_names_map={0:'survive', 1:'death'},
                              cutoff=p,
                              title='Confusion matrix',
                              cmap=None,
                              normalize=False)
    Citiation
    ---------
    http://scikit-learn.org/stable/auto_examples/model_selection/plot_confusion_matrix.html
    """
    if cutoff is not None:
        y_pred_labels = []
        
        for pred in y_pred:
            
            probab = None
            try: 
                probab = pred[1]
            except:
                if isinstance(pred, int):
                    probab = pred
                else:
                    raise

            if probab > cutoff:
                y_pred_labels.append(1)
            else:
                y_pred_labels.append(0)
        
        y_pred = y_pred_labels
    
    target_names = target_names_map.values()
    labels = target_names_map.keys()
    
    cm = confusion_matrix(y_true, y_pred, labels=labels)

    accuracy = np.trace(cm) / float(np.sum(cm))
    misclass = 1 - accuracy

    if cmap is None:
        cmap = plt.get_cmap('Blues')

    plt.figure(figsize=(8, 6))
    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()

    if target_names is not None:
        tick_marks = np.arange(len(target_names))
        plt.xticks(tick_marks, target_names, rotation=45)
        plt.yticks(tick_marks, target_names)
        
    if len(target_names_map.keys()) == 2:
        prec = cm[1][1]/float(cm[1][1] + cm[0][1])
        recall = cm[1][1]/float(cm[1][1] + cm[1][0])
        f1 = 2.0 * prec * recall / float(prec + recall)

    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]

    thresh = cm.max() / 1.5 if normalize else cm.max() / 2
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        if normalize:
            plt.text(j, i, "{:0.4f}".format(cm[i, j]),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")
        else:
            plt.text(j, i, "{:,}".format(cm[i, j]),
                     horizontalalignment="center",
                     color="white" if cm[i, j] > thresh else "black")

    if plt_show:
        plt.tight_layout()
        plt.ylabel('True label')
        plt.xlabel('Predicted label\naccuracy={:0.4f}; misclass={:0.4f}'.format(accuracy, misclass))
        plt.show()
    else:
        plt.close()
        
    if len(target_names_map.keys()) == 2:
        return cm, prec, recall, f1
    
    return cm
    
def normalizedf(df):
    '''
    Normalizes dataframe columns to 1. Send in slice of those columns
    that have to be normalized.
    '''
    df = df.div(df.sum(axis=1), axis=0)
    return df
    
    
def dfcorrelationsplot(df):
    '''
    Just using the simple df.corr() of pandas in addition to ready made easy plot
    for visualizing feature correlations
    
    df: send in the features+target columns only
    '''
    sns.set(style="white")
    
    # Compute the correlation matrix
    corr = df.corr()
    
    # Set up the matplotlib figure
    f, ax = plt.subplots(figsize=(11, 9))
    
    # Generate a custom diverging colormap
    cmap = sns.diverging_palette(220, 10, as_cmap=True)
    
    # Draw the heatmap with the mask and correct aspect ratio
    sns.heatmap(corr, cmap=cmap, vmax=.3, center=0,
                square=True, linewidths=.5, cbar_kws={"shrink": .5})
    
    plt.show()
    return corr

    
# Dealing with categorical features Way 1
def target_encode(trn_series=None, tst_series=None, target=None, min_samples_leaf=1,
                  smoothing=1, noise_level=0):
    """
    Target Encoding for Categorical Features! An alternative to OneHot Encoding. But with a risk of GT leakage.
    This converts Categorical to Numerical fields.
    
    Tested this on Binary class problem with class 0 and 1. 
    Use min_samples_leaf as the minimum number of Class 1 samples to be present for that categorical field group-byed.
    More is the min_samples_leaf, more will be the weight of the cat col mean assuming that Class 0 is more more dominant than Class 1 (imbalance dataset)
    so that having Class 1 values more is "good" weight.
    
    Usage:
    Example - Do Column by Column

    for f in catcols:
        train_df[f + "_new"], test_df[f + "_new"] = target_encode(trn_series=train_df[f],
                                            tst_series=test_df[f],
                                            target=train_df['target'],
                                            min_samples_leaf=200,
                                            smoothing=10,
                                            noise_level=0) 
    
    min_samples_leaf define a threshold where prior and target mean (for a given category value) have the same weight. 
    Below the threshold prior becomes more important and above mean becomes more important.

    How weight behaves against value counts is controlled by smoothing parameter
    
    Smoothing is computed like in the following paper by Daniele Micci-Barreca
    https://kaggle2.blob.core.windows.net/forum-message-attachments/225952/7441/high%20cardinality%20categoricals.pdf
    trn_series : training categorical feature as a pd.Series
    tst_series : test categorical feature as a pd.Series
    target : target data as a pd.Series
    min_samples_leaf (int) : minimum samples to take category average into account
    smoothing (int) : smoothing effect to balance categorical average vs prior
    """
    
    def add_noise(series, noise_level):
        return series * (1 + noise_level * np.random.randn(len(series)))
        
    
    assert len(trn_series) == len(target)
    assert trn_series.name == tst_series.name
    
    temp = pd.concat([trn_series, target], axis=1)
    
    # Compute target mean
    averages = temp.groupby(by=trn_series.name)[target.name].agg(["mean", "count"])
    
    # Compute smoothing
    smoothing = 1 / (1 + np.exp(-(averages["count"] - min_samples_leaf) / smoothing))
    
    # Apply average function to all target data
    prior = target.mean()
    
    # The bigger the count the less full_avg is taken into account
    averages[target.name] = prior * (1 - smoothing) + averages["mean"] * smoothing
    averages.drop(["mean", "count"], axis=1, inplace=True)
    
    # Apply averages to trn and tst series
    ft_trn_series = pd.merge(
        trn_series.to_frame(trn_series.name),
        averages.reset_index().rename(columns={'index': target.name, target.name: 'average'}),
        on=trn_series.name,
        how='left')['average'].rename(trn_series.name + '_mean').fillna(prior)
        
    # pd.merge does not keep the index so restore it
    ft_trn_series.index = trn_series.index
    ft_tst_series = pd.merge(
        tst_series.to_frame(tst_series.name),
        averages.reset_index().rename(columns={'index': target.name, target.name: 'average'}),
        on=tst_series.name,
        how='left')['average'].rename(trn_series.name + '_mean').fillna(prior)
        
    # pd.merge does not keep the index so restore it
    ft_tst_series.index = tst_series.index
    
    return add_noise(ft_trn_series, noise_level), add_noise(ft_tst_series, noise_level)
    
    
# Dealing with Categorical features Way 2    
def doOneHot(df1, ranges):
    '''
    Ready made column one hot function. Use for categorical features especially when using tree based classifiers.
    Pass in the ranges in the format list of list [[column_name, range_list],...] - this should be across the train+test set, mind you.
    Pass in the df.    
    '''
    df = df1.copy() 
    catcolumns = [i[0] for i in ranges]
    print('Original shape: ', df.shape)
    dummydf = df.head(1).copy()   
    dummydf_full = None
    
    for i in ranges:
        for j in i[1]:
            dummydf[i[0]] = j
            if dummydf_full is None:
                dummydf_full = dummydf.copy()
            else:
                dummydf_full = dummydf_full.append(dummydf.copy())

    
    #dummydf_full = pd.DataFrame(dummyrows)
    #dummydf_full.columns = df.columns
    print('Dummy rows shape: ', dummydf_full.shape)
    print('One Hotting...')
    
    df['type'] = 'data'
    dummydf_full['type'] = 'dummy'
    dfappended = df.append(dummydf_full)
    
    dfonehot = pd.get_dummies(dfappended, columns=catcolumns)
    
    finaldf = dfonehot[(dfonehot['type']=='data')]
    
    del finaldf['type']
    print('One hot done. New shape: ', finaldf.shape)
    
    return finaldf.copy() 
    
def hashfile(path, blocksize = 65536, mode='binary', alg='sha256'):
    if mode=='binary':
        afile = open(path, 'rb')
    elif mode=='text':
        afile = open(path, 'r')
    if alg=='md5':
        hasher = hashlib.md5()
    elif alg == 'sha256':
        hasher = hashlib.sha256()
    else:
        print('Bad algorithm.')
        return
    buf = afile.read(blocksize)
    while len(buf) > 0:
        hasher.update(buf)
        buf = afile.read(blocksize)
    afile.close()
    return hasher.hexdigest()
    

# REMOVE CONTENT DUPLICATES 
def findDup(parentFolder, listOfPaths=None, mode='binary'):
    '''
    Dups in format {hash:[names]}
    
    if you want to crawl into the parent folder give that. If you have a list of paths,
    pass the list to the second argument. Second one overrides first one.
    
    mode: can be binary or text

    ''' 
    
    dups = {}
    
    if listOfPaths is None:
        for dirName, subdirs, fileList in os.walk(parentFolder):
            print('Scanning %s...' % dirName)
            for filename in fileList:
                # Get the path to the file
                path = os.path.join(dirName, filename)
                # Calculate hash
                file_hash = hashfile(path)
                # Add or append the file path
                if file_hash in dups:
                    dups[file_hash].append(path)
                else:
                    dups[file_hash] = [path]
    else:
        for path in listOfPaths:
            # Calculate hash
            file_hash = hashfile(path)
            # Add or append the file path
            if file_hash in dups:
                dups[file_hash].append(path)
            else:
                dups[file_hash] = [path]
            
    return dups
    
    
def histogram_equalize_data(data_array, inverse_transform=False, bins=None, 
                            lossless=True, loss_sensitivity='1x', dont_touch_value=0, plot=False, dfhist=None,
                            is_image_intensities=False):
    '''
    Check https://en.wikipedia.org/wiki/Histogram_equalization
    
    This is generally mentioned in Image processing. But it should be of very much interest also to
    apply the same technique to general arrays of data in a lossless manner, not necessarily only for images.
    
    Here is my implementation for that -    
    
    + data_array - expecting a 1D numpy array of flattened data input
    + inverse_transform - the map is a 1-1 map from a equalized histogram back to the original one
    if and only if lossless is True. Else, you will get back the values but a slight error of the 
    order of the bin-size.
    + bins - Number of bins. If none then this is equal to len of the input array
    + lossless - if True, irrespective of what is bins passed, bins is set to len of input array
    + loss_sensitivity - if loss sensitivity is Nx then the bins are chosen N*len of data array
    + dont_touch_value - if this value is present in the input, that will not be changed and 
    will remain the same value for the output. if this is None, then all may change
    + if plot is True and if data_array is 2D
    + dfhist - Pandas dataframe. Needed and cannot be None if using inverse_transform. 
    This is same as the output mapping_df return value
    + is_image_intensities - if True then bins used will be 255 
    
    Returns - 
    
    + new_data_array : Transformed data array according to requirements
    + dfhist : dataframe is returned with data requried to map back - Needed if using inverse later.
    
    '''
    if plot:
        plt.figure()
    if lossless or bins is None:
        bins = len(data_array) * int(loss_sensitivity.split('x')[0])
        if is_image_intensities:
            bins=255
        
    mind = min(data_array)
    maxd = max(data_array)
    
    bins = np.linspace(mind, maxd, bins+2) # fixed number of bins
    
    
    plt.subplot(121)
    plt.xlim([mind, maxd])
    plot1 = plt.hist(data_array, bins=bins, alpha=0.5)
    plt.title('Input Histogram')
    plt.xlabel('Values')
    plt.ylabel('count')
    
    
    if not inverse_transform:
    
        dfhist = pd.DataFrame()
        dfhist['inputbins'] = plot1[1][:-1]
        dfhist['freq'] = plot1[0]
        dfhist['freq_cumsum'] = dfhist['freq'].values.cumsum()
        dfhist['normalized_cumsum'] = dfhist['freq_cumsum']/float(len(data_array))

        dfhist['remap_values'] = mind + dfhist['normalized_cumsum']*float(maxd - mind)


        # map the actual values back 
        bins = dfhist['inputbins'].values
        newvaluesoutput = dfhist.loc[np.digitize(data_array, bins)-1]['remap_values'].values

        if dont_touch_value is not None:
            newvaluesoutput[np.where(data_array == dont_touch_value)[0]]=dont_touch_value 
            # keeping 0 values as 0 only 


        
        plt.subplot(122)
        plt.xlim([mind, maxd])
        plot1 = plt.hist(newvaluesoutput, bins=bins, alpha=0.5)
        plt.title('Output Equalized Histogram')
        plt.xlabel('Values')
        plt.ylabel('count')


        if plot:
            plt.tight_layout()
            plt.show()


        return newvaluesoutput, dfhist.copy()


    else: # inverse_transform
        if dfhist is None:
            raise        
        
        invbins = dfhist['remap_values'].values
        
        # for this case data_array is the equalized format
        oldoutput = dfhist.loc[np.digitize(data_array, invbins)-1]['inputbins'].values
        
        plt.subplot(122)
        plt.xlim([mind, maxd])
        plot1 = plt.hist(oldoutput, bins=bins, alpha=0.5)
        plt.title('Output Restored Histogram')
        plt.xlabel('Values')
        plt.ylabel('count')


        if plot:
            plt.tight_layout()
            plt.show()
        
        
        return oldoutput, dfhist.copy()  
    
    
def RankAverager(valpreds, testpreds, predcol='pred', scale_test_proba=False):
    '''
    Expects <predcol> as the column for prediction values that need be ranked ascending wise - say Class 1. 
    Suitable for Binary class problems.
    Output ranks are displayed in column 'rank_avg_<predcol>' and 'rank_avg_<predcol>_proba' for Class 1.
    
    scale_test_proba scales the rank averaged probabilities from 0 to 1 so the minimum is set 0 and the maximum
    goes to 1 in the Test set. So it is very important to only use this iff your tests predictions have
    a lot of rows. This is generally used in case you are going to average the output probs with some
    other model later.
    
    Very efficient implementation! Uses Binary Search.
    '''
    print('Val: ', valpreds.shape)
    print('Test: ',testpreds.shape)
    
    valpreds['rank_type'] = 'validation'
    testpreds['rank_type'] = 'test'
    
    valpreds = valpreds.sort_values(by=predcol, ascending=True)
    
    valpreds.reset_index(drop=True, inplace=True)
    valpreds['rank_id'] = np.arange(valpreds.shape[0])
    
    testpreds.reset_index(drop=True, inplace=True)
    testpreds['rank_id'] = np.arange(testpreds.shape[0])
    
    rank_avgs = valpreds[predcol].searchsorted(testpreds[predcol]) + 1
    
    testpreds['rankavg_'+predcol]  = rank_avgs  
    
    if scale_test_proba:
        proba = np.array(rank_avgs)/float(valpreds.shape[0]+1)        
        proba = proba - np.min(proba)
        proba = proba/np.max(proba)        
        testpreds['rankavg_'+predcol+'_proba']  = proba
    else:
        testpreds['rankavg_'+predcol+'_proba']  = np.array(rank_avgs)/float(valpreds.shape[0]+1)
    
    return testpreds.copy() 
    
def preds_averager(preds, weights=None, type='AM', convert_to_ranks=False, normalize=True):
    '''
    preds is a list of predictions from predictors(numpy) taken directly from 
    predict methods of classifiers. that is they should contain only the prediction numpy columns.
    
    AM - Arithmetic Mean
    GM - Geometric Mean
    HM - Harmonic Mean 
    
    convert_to_ranks: Converts the predictions into ranks per prediction array in the preds list.
    So, obvly, this doesnt make sense when predicting one by one. But when predictin in bulk at once (eg. Public LB of Kaggle),
    you may try this to kinda overfit LB in some sense! In fact, such an ensemble of 4 models in Porto Seguro gave
    top Public LB (Private not guaranteed!).
    
    Normalization of preds is done.
    '''
   
    if weights is None:
        weights = np.ones((len(preds),), dtype=np.float)
        
    if convert_to_ranks:
        preds_new = []
        for i in preds:
            df = pd.DataFrame(i)
            df = df.rank()/ df.shape[0]
            
            if normalize:
                if df.shape[1]>1: # if more than one prediction column
                    df = normalizedf(df)
            
            preds_new.append(df.values)
        
        preds = preds_new
    
    if len(preds) == 1:
        return preds[0]
    elif len(preds) == 0:
        return None
    
    ans = []
    if type=='AM':
        ans = preds[0]*weights[0]
        counter = 1
        for i in preds[1:]:
            ans = ans + i*weights[counter]
            counter += 1
        
        ans = ans/float(sum(weights))
        
    if type=='GM':
        weights = np.array(weights)
        weights = weights / np.sum(weights)
        
        ans = preds[0]**weights[0]
        counter = 1
        for i in preds[1:]:
            ans = ans*(i**weights[counter])
            counter +=1
        
        
    if type== 'HM': 
        
        invans = float(weights[0])/preds[0]
        counter = 1
        for i in preds[1:]:
            invans = invans + float(weights[counter])/i
            counter+=1
        ans = (float(sum(weights))*float(len(preds)))/invans
    
    ans = pd.DataFrame(ans)
    if normalize:
        if ans.shape[1]>1: # as if = 1 then all preds will be 1!
            ans = normalizedf(ans)
    ans = ans.values
    return ans
    
    
def desperateFitter(dflist, predcols=['pred'], gtcol='target', thrustMode=False, niters=1000, 
                    metric=['logloss','gini','auc'], is_more_better=True, coarseness=10, custom_weight_functions=[np.exp]):
    '''
    DesperateFitter v1.12 - If you are desperate enough to not try a regression model!
    Iterates through Random weights that sum up to 1 and maximize a 
    measure on a target.
    
    dflist: is the validation predictions of various models (type list)
    
    metric: you may pass multiple metrics as functions in a list. But the best pick would be based on the 
    last member of the list for which is_more_better is applicable
    
    custom_weight_functions: use this to pass a function that weights the individual model scores
    supported only for auc and logloss
    
    thrustMode: When true, takes models pairwise and calculates weights successively greedily starting by
    fitting the best models and then the lesser good models. 
    
    # TODO:
    # Add HM, GM based weights desperateFitter
    
    '''
    
    if metric[-1] == 'auc':
        is_more_better = True
    elif metric[-1] == 'logloss':
        is_more_better = False
        
    def calcMetrics(dfs, weight, silent=True):
        newdf = dfs[0].copy()
        
        for predcol in predcols:
            newdf[predcol] = dfs[0][predcol]*weight[0]
            for j in range(1, len(dfs)):
                newdf[predcol] += dfs[j][predcol]*weight[j]
            
        metric_results = []
        metric_labels = []
        
        if not silent:
            print(weight ,end='  ')
        counter = 0
        for i in metric:
            metric_label = None
            if i == 'auc':
                metric_label='auc'
                i=roc_auc_score
            elif i=='logloss':
                metric_label='ll'
                i=log_loss
            elif i=='gini':
                metric_label='gini'
                i=eval_gini
            else:
                metric_label='metric'+str(counter)
                
            if len(predcols)==1:
                metric_result = i(newdf['target'], newdf[predcols[0]])   
            else:
                metric_result = i(newdf['target'], newdf[predcols])    
            metric_results.append(metric_result)
            metric_labels.append(metric_label)
            
            if not silent:
                print(metric_label, ':', metric_result, '\t', end='')
            
            counter+=1
        
        return metric_labels, metric_results
    
    
    nummodels = len(dflist)   
    
    if nummodels >= coarseness:
        print('Coarness set is not compatible to the number of models input. Adjusting...')
        coarseness = nummodels*3
        
    
    init_weights = np.eye(nummodels).tolist()
    init_weights.append((np.ones((1, nummodels))/float(nummodels)).tolist()[0])
    
   
    print('Init Metrics: ')
    init_metrics = []    
    all_init_metrics = []
    for wt in init_weights:
  
        label, metric_results = calcMetrics(dflist, wt, silent=False)                       
        init_metrics.append(metric_results[-1]) # evaluation based on only the last metric
        all_init_metrics.append(metric_results)
        print('\n')
        
    best_metric = None
    wt_index=None
    if is_more_better:
        best_metric = max(init_metrics)
    else:
        best_metric = min(init_metrics)
    best_weights = init_weights[init_metrics.index(best_metric)]
    
    
    print('\n\nEvaling custom metrics')
    # add custom functions to check performances when weighted by indiv model score
    custom_weights = []
    custom_metrics = []
    
    # identity function
    identityfunc = lambda x: x
    inversefunc = lambda x: 1.0/np.abs(x)
    
    if 'logloss' in metric:
        loglosses = []
        # collect loglosses
        
        for i in range(nummodels):
            loglosses.append(all_init_metrics[i][metric.index('logloss')])
        loglosses = np.array(loglosses)
        
        for wtfunction in custom_weight_functions + [inversefunc]:
            wts = wtfunction(-1.0 * loglosses)
            
            custom_weights.append(wts/np.sum(wts))
    
    if 'auc' in metric:
        aucs = []
        # collect aucs
        
        for i in range(nummodels):
            aucs.append(all_init_metrics[i][metric.index('auc')])
        aucs = np.array(aucs)
        
        for wtfunction in custom_weight_functions + [identityfunc]:
            wts = wtfunction(aucs)
            custom_weights.append(wts/np.sum(wts))
            
    
    for wt in custom_weights:
  
        label, metric_results = calcMetrics(dflist, wt, silent=False)                       
        custom_metrics.append(metric_results[-1]) # evaluation based on only the last metric
        print('\n')
        
    custom_best_metric = None
    if is_more_better:
        custom_best_metric = max(custom_metrics)
        if custom_best_metric>best_metric:
            best_metric = custom_best_metric
            best_weights = custom_weights[custom_metrics.index(custom_best_metric)]
    else:
        custom_best_metric = min(custom_metrics)
        if custom_best_metric<best_metric:
            best_metric = custom_best_metric
            best_weights = custom_weights[custom_metrics.index(custom_best_metric)] 
    
    
    
    print('The best eval metric on initial weights is: ', best_metric, ' with weights: ', 
          best_weights, '\n')            
       
    print('\nStarting random search for weights... \n')
    
    if not thrustMode:
        
        for iters in range(niters):
            randnums = []
            for x in range(nummodels):
                randnums.append(random.randint(1, int(coarseness)))
            randnums = np.array(randnums)

            randweights = randnums/np.sum(randnums)
            metric_labels, metric_results = calcMetrics(dflist, randweights, silent=True)
            
            if is_more_better:
                if metric_results[-1] > best_metric:
                    best_metric = metric_results[-1]
                    best_weights = randweights
                    
                    print(randweights, end='  ')
                    for i in range(len(metric_labels)):
                        print(metric_labels[i], ':', metric_results[i], '\t', end='')
                    print('\n')
            else:
                if metric_results[-1] < best_metric:
                    best_metric = metric_results[-1]
                    best_weights = randweights
                    
                    print(randweights, end='  ')
                    for i in range(len(metric_labels)):
                        print(metric_labels[i], ':', metric_results[i], '\t', end='')
                    print('\n')
                        
    else: # thrust mode!
        
        # First sort the models based on their individual goodness
        model_priority = []
        init_metrics_top = init_metrics[:-1].copy()
        
        init_metrics_top_sorted = init_metrics_top.copy()
        if is_more_better:
            init_metrics_top_sorted.sort(reverse=True)
        else:
            init_metrics_top_sorted.sort()
            
        for i in init_metrics_top_sorted:
            model_priority.append(init_metrics_top.index(i))
        
        print('\nModel Priority: ', model_priority)
        
        
        df1 = dflist[model_priority[0]].copy()
        print('Thrusting round 1: Models: ', model_priority[0], ' and ', model_priority[1], '\n')
        
        best_thrust_weights = []
        for i in range(1, nummodels):
            if i!=1:
                print('\nIncremental Thrusting ',i,' with Model', model_priority[i],'\n')
            df2 = dflist[model_priority[i]].copy()
            
            goodweights12 = None 
            goodeval = None
            
            nprange = np.arange(0, 1, 1.0/coarseness)[::-1]
            nprange = np.append(1.0, nprange)
            for weight1 in nprange:
                
                weights12 = [weight1, 1.0-weight1]
                metric_labels, metric_results = calcMetrics([df1, df2], weights12, silent=True)

                if goodeval is None:
                    goodeval = metric_results[-1]
                    goodweights12 = weights12
                    print(goodweights12, end='  ')
                    for i in range(len(metric_labels)):
                        print(metric_labels[i], ':', metric_results[i], '\t', end='')
                    print('\n')
                    
                else:
                    
                    if is_more_better:
                        if metric_results[-1] > goodeval:
                            goodeval = metric_results[-1]
                            goodweights12 = weights12

                            print(goodweights12, end='  ')
                            for i in range(len(metric_labels)):
                                print(metric_labels[i], ':', metric_results[i], '\t', end='')
                            print('\n')
                    else:
                        if metric_results[-1] < goodeval:
                            goodeval = metric_results[-1]
                            goodweights12 = weights12

                            print(goodweights12, end='  ')
                            for i in range(len(metric_labels)):
                                print(metric_labels[i], ':', metric_results[i], '\t', end='')
                            print('\n')
                            
            best_thrust_weights.append(goodweights12)
            
            df1[predcols] = df1[predcols]*goodweights12[0] + df2[predcols]*goodweights12[1]
            
        
        print(best_thrust_weights)
        
        final_thrust_weights = np.array(best_thrust_weights[0].copy())
        
        for j in range(1, len(best_thrust_weights)):
            
            final_thrust_weights = final_thrust_weights*best_thrust_weights[j][0]
            final_thrust_weights = final_thrust_weights.tolist()
            final_thrust_weights.append(best_thrust_weights[j][1])
            final_thrust_weights = np.array(final_thrust_weights)
            
        final_thrust_weights = final_thrust_weights.tolist()
        
        # get the final thrust weights in the right order 
        final_thrust_weights_right_order = []
        
        for i in range(len(model_priority)):
            final_thrust_weights_right_order.append(final_thrust_weights[model_priority.index(i)])        
        
        best_weights = final_thrust_weights_right_order
        
    
    metric_labels, metric_results = calcMetrics(dflist, best_weights, silent=True)

    print('\n\nThe best eval is: ', metric_labels, ' - ', metric_results, ' with weights: ', 
      best_weights, '\n')   
    return best_weights, metric_labels, metric_results


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
        sum_std = abs(std1+std0) #abs(std1-std0) it should be summed not added as you need least variance together
        try:
            significance_measure = diff_mean/(sum_std * 0.5)
        except:
            significance_measure = None
        
        results.append([i, mean0, std0, mean1, std1, diff_mean, sum_std, significance_measure])
        
    results = pd.DataFrame(results)
    results.columns = 'col,mean0,std0,mean1,std1,diff_mean,sum_std,significance_measure'.split(',')
    
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

# easy pickles
def get(name):
    f=open(name, 'rb')
    try:
        mod = pickle.load(f)
    except:
        mod = pickle.load(f, encoding='latin1') # to resolve python 2 vs 3 incompatibility of pickles
    f.close()
    return mod

def put(path, obj):
   f=open(path, 'wb')
   pickle.dump(obj, f)
   f.close()
   return True

# saving huge arrays without loss of precision or disk size constraint
def save_array(fname, arr):
    c=bcolz.carray(arr, rootdir=fname, mode='w')
    c.flush()


def load_array(fname):
    return bcolz.open(fname)[:]



# Criag Glastonbury 23rd on PB LB (0.5 logloss) did a preprocessing of normalizing the RGB histogram with
# Obvly it gave him great results than us (~1 logloss) :/
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
    
