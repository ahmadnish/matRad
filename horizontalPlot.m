function horizontalPlot(inputcube, dosecube, ii)
%%%%%%%
% Code to plot CT and MC dose alligned in horizontal direction
% To be used with the plottingHorizontal stash applied on the branch

figure, set(gcf, 'Units', 'Normalized', 'OuterPosition', [0, 0, .6, .96]);

ax1 = subplot(211); imagesc(squeeze(inputcube(8,:,:)))

xticklabels({'20', '40', '60', '80', '100', '120', '140', '160'})
yticklabels({'4', '8',  '12', '16', '20', '24', '28'})
ylabel ('y [mm]', 'FontWeight', 'bold')

ax2 = subplot(212); imagesc(squeeze(dosecube(8, :, :)))

colormap(ax2, 'jet')
colormap(ax1, 'gray')


xticklabels({'20', '40', '60', '80', '100', '120', '140', '160'})
yticklabels({'4', '8',  '12', '16', '20', '24', '28'})
xlabel ('x [mm]', 'FontWeight', 'bold')
ylabel ('y [mm]', 'FontWeight', 'bold')

set(ax1, 'FontSize', 20, 'FontName', 'FixedWidth')
set(ax2, 'FontSize', 20, 'FontName', 'FixedWidth')


print(gcf, ['C:\masterThesis\tex\img\horiz\horizontal_', num2str(ii), '.jpg'], '-djpeg', '-r300')

end
