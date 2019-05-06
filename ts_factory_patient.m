%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% Script for preparing patient training set for ANN 
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc,clear
addpath(genpath(pwd))

taskNumber = 18;
foldername = ['C:\matRad\nishTopas\task_', num2str(taskNumber, '%.2u')];

% set up the folder
if exist(foldername, 'dir') ~= 7
    mkdir(foldername)
    mkdir([foldername, '\auxiliary'])
    mkdir([foldername, '\matfiles'])
    addpath(genpath(foldername))
end


load protons_generic_TOPAS_cropped.mat
particleEnergies = [machine.data.energy];

gantryAngles = 0:5:355;
% couchAngles = 0:5:355;
isoCenterShift = - 20 : 5 : 20;

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
tic
Ws = zeros(numOfSamples, 1);
for i = 1:numOfSamples
    
    disp(i)
    
    [ct, cst, pln, dij, stf, resultGUI] = doseCalc_patient(vars(i));
    close

    
    filename1 = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/matfiles/topas_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    filename2 = ['C:/matRad/nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
%     filename3 = ['./nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.fig'];
%     filename4 = ['./nishTopas/task_', num2str(taskNumber, '%.2u'), '/auxiliary/aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.png'];
    Vars = vars(i);
    
    save(filename2, 'ct', 'cst', 'pln', 'dij', 'resultGUI', 'stf', 'Vars');
    
    % plot the instance
%     plane = 3;
%     slice = round(pln.propStf.isoCenter(1,3)./ct.resolution.z);
%     doseWindow = [0.001 max([resultGUI.physicalDose(:)])];
%     
%     matRad_plotSliceWrapper(gca,ct,cst,1,resultGUI.physicalDose,plane,slice,[],0.75,colorcube,[],doseWindow,0.01:.002:max(resultGUI.physicalDose(:)));
%     saveas(gcf, filename3)
%     saveas(gcf, filename4)
%     close
    %
    
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