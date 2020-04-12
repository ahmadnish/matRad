clear

load('MonteCarlo.mat')
tmp = load('/home/nish/twoTb/Paper/Task_13_000008/final_13_001647.mat');
uniq = unique(tmp.ct.cubeHU{1});

% inputcube = ct.cube{1}(40:99,73:87, 73:87);
% dosecube = resultGUI.MC_physicalDose(40:99,73:87, 73:87);
% 
% inputcube_slab = tmp.ct.cube{1}(40:99,73:87, 73:87);
% dosecube_slab = tmp.resultGUI.MC_physicalDose(40:99,73:87, 73:87);
% 
% inputcube = permute(inputcube, [3,2,1]);
% dosecube = permute(dosecube, [3,2,1]);
% inputcube_slab = permute(inputcube_slab, [3,2,1]);
% dosecube_slab = permute(dosecube_slab, [3,2,1]);



dosecube = resultGUI.MC_physicalDose(41:100, 73:87, 73:87);
ct.cubeHU{1} = ct.cubeHU{1}(41:100, 73:87, 73:87);
ct.cubeDim = size(ct.cubeHU{1});
ct = matRad_calcWaterEqD(ct, pln);

dosecube_slab = tmp.resultGUI.MC_physicalDose(41:100, 73:87, 73:87);
tmp.ct.cubeHU{1} = tmp.ct.cubeHU{1}(41:100, 73:87, 73:87);
tmp.ct.cubeDim = size(tmp.ct.cubeHU{1});
tmp.ct = matRad_calcWaterEqD(tmp.ct, pln);


ct.cubeHU{1}(1) = uniq(1);
ct.cubeHU{1}(2) = uniq(3);

tmp.ct.cubeHU{1}(1) = uniq(1);


maxx = max([max(dosecube_slab(:)), max(dosecube(:))]+0.001);

f = figure;
set(gcf, 'Units', 'Normalized', 'OuterPosition', [0, 0, 1, 1]);
ax_1 = subplot(211);

[hCMap,hDose,hCt,hContour,hIsoDose] = matRad_plotSliceWrapper(gca, ct, cst, 1 , dosecube, 3, 8, [], 0.75, colorcube,[],[0 maxx],[0.01:.01:maxx]);

ylabel(hCMap, 'Physical Dose [Gy]', 'FontName', 'Liberation Serif', 'FontSize', 15, 'FontWeight', 'normal')

xxlim = xlim
xxticks = [xxlim(1):5:xxlim(2)]
set(gca, 'XTick', xxticks)
set(gca, 'XTickLabel', (xxticks-.5)*2)
yylim = ylim;
yyticks = [yylim(1):2.5:yylim(2)]
set(gca, 'yTick', yyticks)
set(gca, 'yTickLabel', (yyticks-.5)*2)
set(gca, 'FontSize', 15, 'FontName', 'Liberation Serif', 'FontWeight', 'normal')

ax_2 = subplot(212);

[hCMap,hDose,hCt,hContour,hIsoDose] = matRad_plotSliceWrapper(gca, tmp.ct, tmp.cst, 1 , dosecube_slab, 3, 8, [], 0.75, colorcube,[],[0 maxx],[0.01:.01:maxx]);

ylabel(hCMap, 'Physical Dose [Gy]', 'FontName', 'Liberation Serif', 'FontSize', 15, 'FontWeight', 'normal')

xxlim = xlim
xxticks = [xxlim(1):5:xxlim(2)]
set(gca, 'XTick', xxticks)
set(gca, 'XTickLabel', (xxticks-.5)*2)
yylim = ylim;
yyticks = [yylim(1):2.5:yylim(2)]
set(gca, 'yTick', yyticks)
set(gca, 'yTickLabel', (yyticks-.5)*2)
set(gca, 'FontSize', 15, 'FontName', 'Liberation Serif', 'FontWeight', 'normal')


% scaleLabelX = 1.1;
% fontsize = 20
% 
% tickdistX = 12.5; tickdistY = 5;
% XXtick = [0 : tickdistX : size(inputcube, 3)];
% YYtick = [0 : tickdistY : size(inputcube, 2)];
% 
% 
% figure
% set(gcf, 'Color', 'w');
% 
% ax1 = subplot(211);
% 
% im_1 = imagesc(squeeze(inputcube_slab(8,:,:)));
% hcb_1 = colorbar();
% cmap_1 =colormap(ax1, 'gray');
% ylabel(hcb_1, 'RSP', 'FontName', 'Liberation Serif', 'FontSize', fontsize, 'FontWeight', 'normal')
% 
% ticker(gca, 2, XXtick, YYtick)
% 
% % axis labels
% Xlm = xlim; Ylm = ylim;
% ylabel('mm', 'Position', [0, scaleLabelX * Ylm(1)], 'FontName', 'Liberation Serif', 'FontSize', fontsize)
% xlabel('mm', 'Position', [Xlm(2), scaleLabelX * Ylm(2)], 'FontName', 'Liberation Serif', 'FontSize', fontsize)
% 
% title('Extracted CT cube input')
% set(gca, 'FontSize', fontsize, 'FontName', 'Liberation Serif', 'FontWeight', 'normal')
% 
% hold on
% % ax2 = subplot(212);
% im_2 = imagesc(squeeze(dosecube_slab(8,:,:)));
% hcb_2 = colorbar();
% ylabel(hcb_2, 'Physical Dose [Gy]', 'FontName', 'Liberation Serif', 'FontSize', fontsize, 'FontWeight', 'normal')
% 
% ticker(gca, 2, XXtick, YYtick)
% 
% % axis labels
% Xlm = xlim; Ylm = ylim;
% ylabel('mm', 'Position', [0, scaleLabelX * Ylm(1)], 'FontName', 'Liberation Serif', 'FontSize', fontsize)
% xlabel('mm', 'Position', [Xlm(2), scaleLabelX * Ylm(2)], 'FontName', 'Liberation Serif', 'FontSize', fontsize)
% 
% cmap_2 = colormap(ax2, 'jet');
% 
% title('Extracted dose cube ground truth')
% set(gca, 'FontSize', fontsize, 'FontName', 'Liberation Serif', 'FontWeight', 'normal')
% set(gcf, 'Units', 'Normalized', 'OuterPosition', [0, 0, .95, .75]);
% 
% 
% 
% 
% function ticker(h, scaling, xticks, yticks)
% 
% set(h, 'FontSize', 20, 'FontName', 'Liberation Serif')
% 
% set(h, 'XTick', xticks)
% set(h, 'YTick', yticks)
% set(h, 'XTickLabel', xticks*scaling)
% set(h, 'YTickLabel', yticks*scaling)
% 
% end
