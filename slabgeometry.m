% function slabgeometry(gantryAngle, couchAngle)
clc,clear, close all

load BOXPHANTOM_2mm.mat

ct_org = ct;

%%
pln.radiationMode = 'protons';
pln.machine = 'generic_TOPAS_cropped';
% pln.machine = 'Generic'
%%
pln.numOfFractions        = 1;
pln.propStf.gantryAngles  = 0;
pln.propStf.couchAngles   = 0;
pln.propStf.bixelWidth    = 150;
pln.propStf.longitudinalSpotSpacing = 150;
pln.propStf.numOfBeams    = numel(pln.propStf.gantryAngles);
pln.propStf.isoCenter     = ones(pln.propStf.numOfBeams,1) * matRad_getIsoCenter(cst,ct,0);
pln.propOpt.runDAO        = 0;
pln.propOpt.runSequencing = 0;

cst{2,6}.dose = 146;

% pln.bioParam = matRad_bioModel(pln.radiationMode, quantityOpt, modelName);
pln.propOpt.bioOptimization = 'none';
% pln.multScen = matRad_multScen(ct, 'nomScen');
%% define slap geometry
slice = round(pln.propStf.isoCenter(1,3)./ct.resolution.z);
scs = 8;

for ii = 4
    slab_x = -2; % relevant to isocenter in x direction
    slab_y = ii * -10; % relevant to isocenter in y direction

    geo = [3 15 3]; % geometry of the slab

    slab_dim(1) = (2*geo(1) + 1) * ct.resolution.y;
    slab_dim(2) = (2*geo(2) + 1) * ct.resolution.x;
    slab_dim(3) = (2*geo(3) + 1) * ct.resolution.z;

    slab_loc = pln.propStf.isoCenter;

    slab_loc(1) = slab_loc(1) + slab_y; % moving y dimension
    slab_loc(2) = slab_loc(2) + slab_x;  % moving x dimension

    
    slab_loc(1) = floor(slab_loc(1)/ct.resolution.y);
    slab_loc(2) = floor(slab_loc(2)/ct.resolution.x);
    slab_loc(3) = floor(slab_loc(3)/ct.resolution.z);
    
    theta = pi;
    
    for jj = 0 % zero means no change
        
        mask = zeros(ct.cubeDim);
        
        tform = affine3d([1         0               0                0; ...
                          0         cos(jj * theta) sin(jj * theta)  0; ...
                          0         -sin(jj *theta) cos(jj * theta)  0; ...
                          0         0               0                1]);
                            
                      
        for i = -geo(1):geo(1)
            for j = -2 * geo(2) : 0
                for z = -geo(3):geo(3)
                    ix = slab_loc + [i, j, z];
                    mask(ix(1),ix(2),ix(3)) = 1;
                end
            end
        end

%         mask = imwarp(mask, tform);
%         subplot(1,2,jj+1)
%         imagesc(mask(:,:,slice))
%         pause(.2)
%         
        ct.cube{1}(mask == 1) = 2;
        ct.cubeHU{1}(mask == 1) = 1024;
%         ct.cube{1} = ct_org.cube{1};
%         ct.cubeHU{1} = ct_org.cubeHU{1};
    end
    %
    stf = matRad_generateStf(ct, cst, pln);
    stf.ray.energy = 116.3620;

    dij = matRad_calcParticleDose(ct,stf,pln,cst);

    resultGUI = matRad_fluenceOptimization(dij,cst,pln);

    filename = ['topas_ws_',int2str(slab_loc(1)),'_',int2str(slab_loc(2)), ...
        '_',int2str(slab_loc(3)),'_',int2str(geo(1)),'_',int2str(geo(2)), ...
        '_',int2str(geo(3))];
    save([filename, '.mat']);
%     nish_Submit_MC_calculation_via_SSH(filename, 1e-3)
%     
    ct.cube{1} = ct_org.cube{1};
    ct.cubeHU{1} = ct_org.cubeHU{1};
end

matRadGUI

%         vis = ct.cube{1};
%         vis (vis == 1) = 0;
%         subplot(221)
%         imagesc(vis(:,:,slice))
%         title(['Z ii = ', num2str(ii), 'jj = ', num2str(jj)])
%         subplot(222)
%         imagesc(squeeze(vis(:,slice,:)))
%         title(['Y ii = ', num2str(ii), 'jj = ', num2str(jj)])
%         subplot(223)
%         imagesc(squeeze(vis(slice,:,:)))
%         title(['X ii = ', num2str(ii), 'jj = ', num2str(jj)])
%         hold on
%         pause(1)
        