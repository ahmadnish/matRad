% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
% % Script for preparing training set for ANN 
% %%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
clc,clear ,tic
%% Write down all the possible values for the parameters
load protons_generic_TOPAS_cropped.mat

particleEnergies = [machine.data.energy];
peakPos = [machine.data.peakPos];

particleEnergies = particleEnergies(7:28); %22 cases
peakPos = peakPos(7:28); 

% slabSPs = 0.00324:.01:2.53061; %253 cases
slabHUs = -1024: 10 : 3071; % 410 cases
slab_goe_xs = 0;
slabGeometeries = ["Rectangle", "Ellipsoid", "Pyramid", "2DPyramid"];
numOfSamples = 1;
%% Random sample from the possible values
vars = struct;
i = 1;
tmp2 = 0;
while (i <= numOfSamples && tmp2 < 10)
    
    vars(i).gantryAngle = 0;
    vars(i).couchAngle = 0;
    vars(i).geoShape = '2DPyramid';
    vars(i).geoSize = [14 16 14]; % size of the geometry in voxels
                                  % for Rectagle:
                                  % for Triangle:
                                  % for Circle:
    
    vars(i).alignment = [-30 -16 0]; % aligns the center point in respect to the
    % isocneter which in turn will be the starting point
    % for building the geometry. y and z are build around
    % this point while x is build toward left or right
    % first dimension y: up to down
    % second dimension x: left to right
    % third dimension
    
%     vars(i).slab_sp = randsample(slabSPs,1); % slab's stopping power
    vars(i).slab_hu = randsample(slabHUs,1); % slab's Hounsfield's unit
    
    vars(i).Energy = randsample(particleEnergies, 1); % desired energy for the particle
    
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

clearvars -except vars numOfSamples

% load('BOXPHANTOM_2mm.mat')
boxSize = 160 * ones(1,3);
res = 2 * ones(1,3);
[ct, cst] = makeBoxphantom(boxSize, res);

for i = 1:numOfSamples
    [ct, cst, pln, stf, resultGUI, mask] = doseCalc(ct, cst, vars(i));
    close
    filename = ['topas_ws_', num2str(i, '%.6u'), '.mat'];
    
    save(filename, 'ct', 'cst', 'pln', 'resultGUI', 'stf');
end

toc