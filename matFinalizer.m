function matFinalizer(taskNumber, startI, endI, imsize, depth)
% function for preparing a final version mat file after topas
% This script designed to be executed in the task_X folder

addpath(genpath(pwd))

if startI >=  endI
    error('start should be smaller than end')
end

foldername = ['C:\matRad\nishTopas\task_',num2str(taskNumber, '%.2u')];

if exist(foldername, 'dir') ~= 7
    error('task number does not exist')
end

inn = 'N';
tic
for i = startI:endI
    disp(['step 1_', num2str(i)])
    clearvars -except taskNumber i foldername inn startI endI cubeExtract imsize depth
    try
        outfile = [foldername ,'\output\ws_topas_', num2str(taskNumber, '%.2u'), '_', num2str(i, '%.6u'), '.mat'];
        auxfile = [foldername,'\auxiliary\aux_', num2str(taskNumber, '%.2u'), '_', num2str(i, '%.6u'), '.mat'];
        finalfile = [foldername,'\final\final_', num2str(taskNumber, '%.2u'), '_', num2str(i, '%.6u'), '.mat'];
        
        load(outfile);
        tmp = load(auxfile);

        cst = tmp.cst;
        dij = tmp.dij;
        resultGUI.physicalDose = tmp.resultGUI.physicalDose;
        
        V = [cst{:,4}];
        V = unique(vertcat(V{:}));
        eraseCtDensMask = ones(prod(ct.cubeDim),1);
        eraseCtDensMask(V) = 0;
        resultGUI.MC_physicalDose(eraseCtDensMask == 1) =  0;
        resultGUI.MC_physicalDose(resultGUI.MC_physicalDose < 1e-4) = 0;
        
        
        
        % check if file exists to avoid overwriting
        if ~isfile(finalfile)
            
            save(finalfile);
            
            if  isfile(finalfile)
                movefile(outfile, 'D:\task_40_backup\output');
                movefile(auxfile, 'D:\task_40_backup\auxiliary');
                movefile(finalfile, 'D:\task_40_backup\final');
                
                if i == startI 
%                     warning('out and aux are being deleted!')
                    toc
                end
                
            end                      
            
        else
            
            warning('Final file already exists!, no saving...')
            
        end
        
        
    catch
        
        warning('wasnt able to load the files - no saving no cube extraction')
        
    end
    
    % performing the cube extraction if it is asked for
    if exist('imsize', 'var')
        
        [inputcube, dosecube, dosecube_phys] = matRad_rayTracingXXX(ct.cube, ...
        {resultGUI.MC_physicalDose}, {resultGUI.physicalDose}, ct.resolution,stf.isoCenter,2, ...
        stf.gantryAngle,stf.couchAngle, imsize, depth);
        
        dosecube = dosecube/resultGUI.w;

        t = dosecube .* inputcube;
        dosecube = 1000 * dosecube / sum(t(:));

        dosecube_phys = dosecube_phys/resultGUI.w;

        t = dosecube_phys .* inputcube;
        dosecube_phys = 1000 * dosecube_phys / sum(t(:));

        save([foldername,'/cubes/inpOutCubes_', num2str(i, '%.6u'), '.mat'], 'inputcube', 'dosecube', 'dosecube_phys');

    end

end