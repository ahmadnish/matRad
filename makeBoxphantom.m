function [ct, cst] = makeBoxphantom(xDim, yDim, zDim)

ct.cubeDim      = [xDim yDim zDim];
ct.resolution.x = 2;
ct.resolution.y = 2;
ct.resolution.z = 2;
ct.numOfCtScen  = 1;
 
% create an ct image series with zeros - it will be filled later
ct.cubeHU{1} = ones(ct.cubeDim) * -1024; % assign HU of Air
ct.cube{1} = zeros(ct.cubeDim);

%% Create the VOI data for the phantom
% Now we define structures a contour for the phantom and a target

ixOAR = 1;
ixPTV = 2;

% define general VOI properties
cst{ixOAR,1} = 0;
cst{ixOAR,2} = 'contour';
cst{ixOAR,3} = 'OAR';

cst{ixPTV,1} = 1;
cst{ixPTV,2} = 'target';
cst{ixPTV,3} = 'TARGET';
 
% define optimization parameter for both VOIs
cst{ixOAR,5}.TissueClass = 1;
cst{ixOAR,5}.alphaX      = 0.1000;
cst{ixOAR,5}.betaX       = 0.0500;
cst{ixOAR,5}.Priority    = 2;
cst{ixOAR,5}.Visible     = 1;
cst{ixOAR,6}.type        = 'square overdosing';
cst{ixOAR,6}.dose        = 5;
cst{ixOAR,6}.penalty     = 100;
cst{ixOAR,6}.EUD         = NaN;
cst{ixOAR,6}.volume      = NaN;
cst{ixOAR,6}.coverage    = NaN;
cst{ixOAR,6}.robustness  = 'none';

cst{ixPTV,5}.TissueClass = 1;
cst{ixPTV,5}.alphaX      = 0.1000;
cst{ixPTV,5}.betaX       = 0.0500;
cst{ixPTV,5}.Priority    = 1;
cst{ixPTV,5}.Visible     = 1;
cst{ixPTV,6}.type        = 'square deviation';
cst{ixPTV,6}.dose        = 146;
cst{ixPTV,6}.penalty     = 800;
cst{ixPTV,6}.EUD         = NaN;
cst{ixPTV,6}.volume      = NaN;
cst{ixPTV,6}.coverage    = NaN;
cst{ixPTV,6}.robustness  = 'none';


%% Lets create either a cubic or a spheric phantom

% first the OAR
cubeHelper = zeros(ct.cubeDim);

      
xLowOAR  = round(xDim/2 - xDim/4);
xHighOAR = round(xDim/2 + xDim/4);
yLowOAR  = round(yDim/2 - yDim/4);
yHighOAR = round(yDim/2 + yDim/4);
zLowOAR  = round(zDim/2 - zDim/4);
zHighOAR = round(zDim/2 + zDim/4);

for x = xLowOAR:1:xHighOAR
    for y = yLowOAR:1:yHighOAR
        for z = zLowOAR:1:zHighOAR
            cubeHelper(x,y,z) = 1;
        end
    end
end


% extract the voxel indices and save it in the cst
cst{ixOAR,4}{1} = find(cubeHelper);


% second the PTV
cubeHelper = zeros(ct.cubeDim);

      
xLowPTV  = round(xDim/2 - xDim/8);
xHighPTV = round(xDim/2 + xDim/8);
yLowPTV  = round(yDim/2 - yDim/8);
yHighPTV = round(yDim/2 + yDim/8);
zLowPTV  = round(zDim/2 - zDim/8);
zHighPTV = round(zDim/2 + zDim/8);

cubeHelper = zeros(ct.cubeDim);

for x = xLowPTV:1:xHighPTV
    for y = yLowPTV:1:yHighPTV
        for z = zLowPTV:1:zHighPTV
            cubeHelper(x,y,z) = 1;
        end
    end
end

% extract the voxel indices and save it in the cst
cst{ixPTV,4}{1} = find(cubeHelper);

%% Assign relative electron densities
vIxOAR = cst{ixOAR,4}{1};
vIxPTV = cst{ixPTV,4}{1};

ct.cubeHU{1}(vIxOAR) = 0;
ct.cubeHU{1}(vIxPTV) = 0;

ct.cube{1}(vIxOAR) = 1;
ct.cube{1}(vIxPTV) = 1;