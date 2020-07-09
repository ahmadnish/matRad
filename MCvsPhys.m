addpath(genpath(pwd))
taskNumber = 21;

foldername = ['~/twoTb/matRad/nishTopas/task_',num2str(taskNumber, '%.2u')];

tic
passes = zeros(1000, 1);
for i = 30:31
    
    disp(['step 1_', num2str(i)])
    clearvars -except taskNumber i foldername  

    finalfile = [foldername,'/finals/final_', num2str(taskNumber, '%.2u'), '_', num2str(i, '%.6u'), '.mat'];

    load(finalfile);

    V = [cst{:,4}];
    V = unique(vertcat(V{:}));
    eraseCtDensMask = ones(prod(ct.cubeDim),1);
    eraseCtDensMask(V) = 0;
    resultGUI.MC_physicalDose(eraseCtDensMask == 1) =  0;
    resultGUI.MC_physicalDose(resultGUI.MC_physicalDose < 1e-4) = 0;
    resultGUI.physicalDose(resultGUI.physicalDose < 1e-4) = 0;


    [inputcube, dosecube, dosecube_phys] = matRad_rayTracingXXX(ct.cube, ...
    {resultGUI.MC_physicalDose}, {resultGUI.physicalDose}, ct.resolution,stf.isoCenter,2, ...
    stf.gantryAngle,stf.couchAngle, 15, 150);

    dosecube = dosecube/resultGUI.w;

    t = dosecube .* inputcube;
    dosecube = 1000 * dosecube / sum(t(:));
    dosecube = permute(dosecube, [3 1 2]);
    
    dosecube_phys = dosecube_phys/resultGUI.w;

    t = dosecube_phys .* inputcube;
    dosecube_phys = 1000 * dosecube_phys / sum(t(:));
    dosecube_phys = permute(dosecube_phys, [3 1 2]);
    
    inputcube = permute(inputcube, [3 1 2]);
    
    [cube, pass] = gammaIndexPlotter_h(inputcube, dosecube, dosecube_phys, true, 8, [.5 2]);
    passes(i) = pass;
    
    export_fig([foldername, '/MCvsPhys/img_', num2str(i, '%.6u')], '-pdf', gcf, '-nocrop')
    
    close

end