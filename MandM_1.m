load('/mnt/nvme-2tb/matRad/nishTopas/task_21/finals/final_21_000007.mat')

ct.cubeHU = ct.cube

V = [cst{:,4}];
V = unique(vertcat(V{:}));
eraseCtDensMask = ones(prod(ct.cubeDim),1);
eraseCtDensMask(V) = 0;
resultGUI.MC_physicalDose(eraseCtDensMask == 1) =  0;
%resultGUI.MC_physicalDose(resultGUI.MC_physicalDose < 1e-4) = 0;


% you want to probably comment out the secion with VOI contouring in
% matRad_plotSliceWrapper.m

% also, if you want to have a shaded version:
    % go to the rayTracingXXX.m and add a HIT voxel variable there
    % get the unique of them
    % and then ct.cubeHT{1}(hit) = ct.cubeHT{1}(hit) * 1.5
   
figure   
[hCMap,hDose,hCt,~,hIsoDose] = nishSliceWrapper(ct, cst, pln,resultGUI.MC_physicalDose);

ylim([45 165])


ylabel(hCMap, 'Physical Dose [Gy]', 'FontName', 'Liberation Serif', 'FontSize', 15, 'FontWeight', 'normal')


set(gca, 'FontSize', 15, 'FontName', 'Liberation Serif', 'FontWeight', 'normal')
set(gcf, 'Units', 'Normalized', 'OuterPosition', [0, 0, .7, 1]);



%% To plot the extracted cube

[inputcube, dosecube, dosecube_phys, hit] = matRad_rayTracingXXX(ct.cube, ...
{resultGUI.MC_physicalDose}, {resultGUI.physicalDose}, ct.resolution,stf.isoCenter,2, ...
stf.gantryAngle,stf.couchAngle, 15, 150);

scaleLabelX = 1.1;
fontsize = 20

tickdistX = 12.5; tickdistY = 5;
XXtick = [0 : tickdistX : size(inputcube, 3)];
YYtick = [0 : tickdistY : size(inputcube, 2)];


figure
set(gcf, 'Color', 'w');

ax1 = subplot(211);

im_1 = imagesc(squeeze(inputcube(8,:,:)));
hcb_1 = colorbar();
cmap_1 =colormap(ax1, 'gray');
ylabel(hcb_1, 'RSP', 'FontName', 'Liberation Serif', 'FontSize', fontsize, 'FontWeight', 'normal')

ticker(gca, 2, XXtick, YYtick)

% axis labels
Xlm = xlim; Ylm = ylim;
ylabel('mm', 'Position', [0, scaleLabelX * Ylm(1)], 'FontName', 'Liberation Serif', 'FontSize', fontsize)
xlabel('mm', 'Position', [Xlm(2), scaleLabelX * Ylm(2)], 'FontName', 'Liberation Serif', 'FontSize', fontsize)

title('Extracted CT cube input')
set(gca, 'FontSize', fontsize, 'FontName', 'Liberation Serif', 'FontWeight', 'normal')


ax2 = subplot(212);
im_2 = imagesc(squeeze(dosecube(8,:,:)));
hcb_2 = colorbar();
ylabel(hcb_2, 'Physical Dose [Gy]', 'FontName', 'Liberation Serif', 'FontSize', fontsize, 'FontWeight', 'normal')

ticker(gca, 2, XXtick, YYtick)

% axis labels
Xlm = xlim; Ylm = ylim;
ylabel('mm', 'Position', [0, scaleLabelX * Ylm(1)], 'FontName', 'Liberation Serif', 'FontSize', fontsize)
xlabel('mm', 'Position', [Xlm(2), scaleLabelX * Ylm(2)], 'FontName', 'Liberation Serif', 'FontSize', fontsize)

cmap_2 = colormap(ax2, 'jet');

title('Extracted dose cube ground truth')
set(gca, 'FontSize', fontsize, 'FontName', 'Liberation Serif', 'FontWeight', 'normal')
set(gcf, 'Units', 'Normalized', 'OuterPosition', [0, 0, .95, .75]);




function ticker(h, scaling, xticks, yticks)

set(h, 'FontSize', 20, 'FontName', 'Liberation Serif')

set(h, 'XTick', xticks)
set(h, 'YTick', yticks)
set(h, 'XTickLabel', xticks*scaling)
set(h, 'YTickLabel', yticks*scaling)

end

%% Notes:

% To fix the problem with matlab2tikz export of multiple color map
% you have to change the entire figure colormap with e.g. colormap('gray')
% for each subplot and collect the respective png file for each colormap
% gray at tikz is /blackwhite
