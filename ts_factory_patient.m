%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Script for preparing patient training set for ANN 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc,clear
addpath(genpath(pwd))

taskNumber = 40;
foldername = ['C:\matRad\nishTopas\task_', num2str(taskNumber, '%.2u')];

% set up the folders
if exist(foldername, 'dir') ~= 7
    mkdir(foldername)
    mkdir([foldername, '\auxiliary'])
    mkdir([foldername, '\matfiles'])
    mkdir([foldername, '\output'])
    mkdir([foldername, '\final'])
    mkdir([foldername, '\cubes'])
    mkdir([foldername, '\figures'])
    addpath(genpath(foldername))
end


% prepare a description file of the task
fid = fopen([foldername, '\discription.txt'], 'wt' );
description = ['Preparing 3000 samples with 3 different energies', ...
    '...'];
% discription = ['Using patient case S000005 from HIT data ', ...
%     '\n to test the network -- all around angles ', ...
%     '\n Preparing ouputs for the PAPER'];
% fprintf( fid, '%\n', discription);
fwrite(fid, description, 'char'); 
fclose(fid);

% Load machine data
load protons_generic_TOPAS_cropped.mat
particleEnergies = [machine.data.energy];

% set up the gantry and iso center shift change domain
gantryAngles = [0:5:355];
% gantryAngles = [290 290];
% couchAngles = 0:5:355;
isoCenterShift = [-40:5:60];

numOfSamples = 3000;
%%
tmp2 = 0;
i = 1;
vars = struct;
while (i <= numOfSamples)
    
    vars(i).gantryAngle = randsample(gantryAngles, 1);
%     vars(i).couchAngle = randsample(couchAngles, 1);
    vars(i).shift = randsample(isoCenterShift, 1);
    vars(i).energy = randsample(particleEnergies([1,16,32]), 1);
    
    
    % check if there is recurrence in sampling
    tmp1 = 1;
    for ii = 1:i-1
        if (isequal(vars(i), vars(ii)))
            tmp1 = 0;
        end
    end
    
    if tmp1
        i = i+1;
    else 
        tmp2 = tmp2+1;
    end
end

save(['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/vars_', num2str(taskNumber, '%.2u'), '.mat'], 'vars');
%%
addpath(genpath(pwd))
tic
Ws = zeros(numOfSamples, 1);
tmp = 0;
for i = 1:numOfSamples
    
    disp(i)
    clearvars -except vars Ws tmp i taskNumber
    
    tmp = load('./Paper_HITS05_2mm.mat');
    ct = tmp.ct;
    cst = tmp.cst;
    clear tmp
    pln.radiationMode = 'protons';
    ct.numOfCtScen = 1;
    ct = matRad_calcWaterEqD(ct, pln);
    
    [ct, cst, pln, dij, stf, resultGUI] = doseCalc_patient(vars(i), ct, cst);
    clc, close

    if isnan(resultGUI.w)
        warning('no fluence were assigned')
        disp(i)
        tmp = tmp + 1;
        continue
    end
    
    
%     
    

%     filename = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/full_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
%     save(filename);

    Vars = vars(i);
    
    filename = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    save(filename, 'cst', 'dij', 'resultGUI', 'Vars');

    filename = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/figures/fig_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u')];
    nishSliceWrapper(ct, cst, pln, resultGUI.physicalDose, true, filename)

    
    % prune the input for topas, save what is necessary
    tt = resultGUI;
    clear resultGUI
    resultGUI.w = tt.w;
    clear tt
    ct = rmfield(ct, 'cubeHU');
    disp(resultGUI.w)
    Ws(i) = resultGUI.w;
%     
    filename = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/matfiles/topas_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    save(filename, 'ct', 'pln', 'resultGUI', 'stf');
    
end
toc