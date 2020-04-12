load('/home/nish/twoTb/matRad/nishTopas/task_21/cubes/inpOutCubes_000007.mat')


max_ct = max(inputcube(:));
min_ct = min(inputcube(:));

window_ct = [min_ct max_ct];

max_dose = max(dosecube(:));
min_dose = min(dosecube(:));

window_dose = [min_dose max_dose];

tickdistX = 2.5; tickdistY = 2.5;
XXtick = [0 : tickdistX : size(inputcube, 1)];
YYtick = [0 : tickdistY : size(inputcube, 2)];

for i=1:10:80
figure
set(gcf, 'units','centimeters','outerposition',[0 0 3.5 5]);
set(gcf, 'color', 'w')
im_1 = imagesc(squeeze(inputcube(:,:, i)));
colormap(gca, 'gray')
caxis(gca, window_ct)
%colorbar()
% title(['slice #' num2str(i), 'in z axis'])
% ticker(gca, 2, XXtick, YYtick)
set(gca,'xtick',[])
set(gca,'xticklabel',[])
set(gca,'ytick',[])
set(gca,'yticklabel',[])
box off
set(gca,'XColor','none')
set(gca,'YColor','none')

export_fig(['../Paper/img/MandM_2_ctSlice_', num2str(i),'.pdf'])

figure
set(gcf, 'units','centimeters','outerposition',[0 0 3.5 5]);
set(gcf, 'color', 'w')

im_2 = imagesc(squeeze(dosecube(:,:, i)))
colormap(gca, 'jet')
caxis(gca, window_dose)
%colorbar()
% title(['slice #' num2str(i), 'in z axis'])
% ticker(gca, 2, XXtick, YYtick)
set(gca,'xtick',[])
set(gca,'xticklabel',[])
set(gca,'ytick',[])
set(gca,'yticklabel',[])
box off
set(gca,'XColor','none')
set(gca,'YColor','none')

export_fig(['../Paper/img/MandM_2_doseSlice_', num2str(i),'.pdf'])
end


function ticker(h, scaling, xticks, yticks)

set(h, 'FontSize', 14, 'FontName', 'Liberation Serif')

set(h, 'XTick', xticks)
set(h, 'YTick', yticks)
set(h, 'XTickLabel', xticks*scaling)
set(h, 'YTickLabel', yticks*scaling)

end