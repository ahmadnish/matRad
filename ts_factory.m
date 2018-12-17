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

slabSPs = 0.00324:.01:2.53061; %253 cases
slab_goe_xs = 0;
slabGeometeries = ["Rectangle", "Ellipsoid", "Pyramid", "2DPyramid"];
numOfSamples = 300;
%% Random sample from the possible values
vars = struct;
i = 1;
while (i <= numOfSamples)
    
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
    
    vars(i).slab_ed = 2; % slab's stopping power
    vars(i).slab_hu = 1024; % slab's Hounsfield's unit
    
    vars(i).Energy = 127.5440; % desired energy for the particle
    
    %     if i ~= 1
    %         % Check if this vars has already been incorporated
    %         for ii = 1:i-1
    %             if isequal(vars, varsHist.(['vars',num2str(ii)]))
    %                 continue
    %             end
    %         end
    %     end
    
    
    %     % Book keeping the vars
    %     varsHist.(['vars',num2str(i)]) = vars;
    tmp = 1;
    for ii = 1:i-1
        if isequal(vars(i), vars(ii))
            tmp = 0;
        end
    end
    
    if tmp
        i = i+1;
    end
    
end

% load('BOXPHANTOM_2mm.mat')
boxSize = 160 * ones(1,3);
res = 2 * ones(1,3);
[ct, cst] = makeBoxphantom(boxSize, res);

for i = 1:numOfSamples
    [ct, cst, pln, stf, resultGUI, mask] = doseCalc(ct, cst, vars(i));
    close
    % filename = ['topas_ws_',int2str(slab_loc(1)),'_',int2str(slab_loc(2)), ...
    %     '_',int2str(slab_loc(3)),'_',int2str(geo(1)),'_',int2str(geo(2)), ...
    %     '_',int2str(geo(3))];
    %
    % filename = ['topas_ws_320Boxphantom'];
    %
    % save([filename, '.mat']);
end

toc