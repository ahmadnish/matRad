% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% % Script for preparing training set for ANN 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc,clear ,tic
%% Write down all the possible values for the parameters
load protons_generic_TOPAS_cropped.mat

finalCubeSize = [80 28 28]; % the extraction cube for ANN

particleEnergies = [machine.data.energy];
peakPos = [machine.data.peakPos];

particleEnergies = particleEnergies(7:28); % 22 cases
peakPos = peakPos(7:28); 

slabSPs = 0.00324:.01:2.53061; % 253 cases

slabXs = 1:finalCubeSize(1)/2; % 41 cases (adaptive)
slabYs = 8:finalCubeSize(2)/2; % 9 cases
slabZs = finalCubeSize(3)/2;   % fixed value

alignmentsX = -40:0; % 41 cases

slab_goe_xs = 0;
% slabGeometeries = ["Rectangle", "Ellipsoid", "Pyramid", "2DPyramid"];
slabGeometeries = ["Rectangle", "2DPyramid"];
numOfSamples = 30;
%% Random sample from the possible values
vars = struct;
i = 1;
tmp2 = 0;
while (i <= numOfSamples && tmp2 < 10)
    
    vars(i).boxSize = 160 * ones(1,3);
    vars(i).res = 2 * ones(1,3);
    vars(i).gantryAngle = 0;
    vars(i).couchAngle = 0;
    vars(i).geoShape = randsample(slabGeometeries, 1);
   
    vars(i).Energy = randsample(particleEnergies, 1); % desired energy for the particle
    peakPosition = peakPos(vars(i).Energy == particleEnergies);
    peakPosition = peakPosition/vars(i).res(3);
    
%     vars(i).geoSize = [40 14 14];
    vars(i).geoSize = zeros(1,3);
    vars(i).geoSize(1) = randsample(slabXs(slabXs < peakPosition/2),1);
    vars(i).geoSize(2) = randsample(slabYs,1);
    vars(i).geoSize(3) = randsample(slabZs,1); % 
%     
    vars(i).alignment = [0 -15 0]; 
    vars(i).alignment(1) = randsample(alignmentsX,1);
    
    % aligns the center point in respect to the
    % isocneter which in turn will be the starting point
    % for building the geometry. y and z are build around
    % this point while x is build toward left or right
    % first dimension y: up to down
    % second dimension x: left to right
    % third dimension
    
    vars(i).slab_sp = randsample(slabSPs,1); % slab's stopping power
    
    
    tmp1 = 1;
    for ii = 1:i-1
        if isequal(vars(i), vars(ii))
            tmp1 = 0;
        end
    end
    
    if tmp1
        i = i+1;
    else 
        tmp2 = tmp2+1;
    end
    
end

save(['vars_', num2str(taskNumber, '%.2u'), '.mat'], 'vars');

auto = 0;
for i = 1:numOfSamples
    [ct, cst, pln, stf, resultGUI, mask] = doseCalc(vars(i));
    close
    matRadGUI
%     if(auto == 0)
%         s = input('press a key to continue:', 's');
%         if( s == 'a')
%             auto = 1;
%         end
%     else
%         pause(3)
%     end
    pause(1)
    
    filename1 = ['topas_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    filename2 = ['aux_', num2str(taskNumber, '%.2u'),'_', num2str(i, '%.6u'), '.mat'];
    v = vars(i);
    save(filename2, 'ct', 'cst', 'pln', 'resultGUI', 'stf', 'v');
    
    tmp = resultGUI;
    clear resultGUI
    resultGUI.w = tmp.w;
    clear tmp
    ct = rmfield(ct, 'cubeHU');
    
    save(filename1, 'ct', 'pln', 'resultGUI', 'stf');
end

toc