%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Script for preparing patient training set for ANN 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc,clear
addpath(genpath(pwd))

taskNumber = 22;
foldername = ['C:\matRad\nishTopas\task_', num2str(taskNumber, '%.2u')];

% set up the folder
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

fid = fopen([foldername, '\discription.txt'], 'wt' );
discription = ['2500 samples of lung, with single energy. \n', ...
    'I am doing this to be sure I have more data\n', ...
    'and also to make sure I am not overfitting\n', ...
    'I will use only 2000 of the data and keep 500 untouched'];
% fprintf( fid, '%\n', discription);
fwrite(fid, discription, 'char');cd 
fclose(fid);


load protons_generic_TOPAS_cropped.mat
particleEnergies = [machine.data.energy];

gantryAngles = 0:5:355;
% couchAngles = 0:5:355;
isoCenterShift = - 100 : 5 : -80

numOfSamples = 1;
%%
tmp2 = 0;
i = 1;
vars = struct;
while (i <= numOfSamples)
    
    vars(i).gantryAngle = randsample(gantryAngles, 1);
%     vars(i).couchAngle = randsample(couchAngles, 1);
    vars(i).shift = randsample(isoCenterShift, 1);
    vars(i).energy = particleEnergies(16);
    
    
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
load('C:/matRad/nishTopas/task_21/vars_21.mat')
addpath(genpath(pwd))
taskNumber = 21;
numOfSamples = 2000;
tic
Ws = zeros(numOfSamples, 1);
tmp = 0;
for i = 795:numOfSamples
    
    disp(i)
    
    [ct, cst, pln, dij, stf, resultGUI] = doseCalc_patient(vars(i));
    clc, close

    if isnan(resultGUI.w)
        warning('no fluence were assigned')
        disp(i)
        tmp = tmp + 1;
        continue
    end
    
    
    
    filename1 = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/matfiles/topas_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    filename2 = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    filename3 = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/figures/fig_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u')];
%     filename3 = ['./nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.fig'];
%     filename4 = ['./nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.png'];
    Vars = vars(i);
    
    save(filename2, 'ct', 'cst', 'pln', 'dij', 'resultGUI', 'stf', 'Vars');
    
%     nishSliceWrapper(ct, cst, pln, resultGUI.physicalDose, true, filename3)

    
    % prune the input for topas, save what is necessary
    tmp = resultGUI;
    clear resultGUI
    resultGUI.w = tmp.w;
    clear tmp
    ct = rmfield(ct, 'cubeHU');
    disp(resultGUI.w)
    Ws(i) = resultGUI.w;
    
    save(filename1, 'ct', 'pln', 'resultGUI', 'stf');
    
end
toc