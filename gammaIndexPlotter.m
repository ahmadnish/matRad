figure
set(gcf, 'Units', 'Normalized', 'OuterPosition', [0, 0.04, .5, 0.96]);



[gammaCube] = matRad_gammaIndex(dose,dose_ann,[2 2 2], [1 2], [], 3);

% for i = 1:15
%     subplot(411);
%     imagesc(squeeze(ct(:,:,i))')
%     colorbar()
%     
%     ax1 = subplot(412);
%     imagesc(squeeze(dose(:,:,i))')
%     colorbar()
%     colormap(gca, 'jet')
%     title(i)
%     ax2 = subplot(413);
%     imagesc(squeeze(dose_ann(:,:,i))')
%     colorbar()
%     colormap(gca, 'jet')
%     
%     % set the colormap limit fixed for both
%     combined = [dose(:,:,i) dose_ann(:,:,i)];
%     mAx = max(combined(:));
%     mIN = min(combined(:));
%     caxis(ax1, [mIN, mAx])
%     caxis(ax2, [mIN, mAx])
%     
%     
%     subplot(414)
%     imagesc(squeeze(gammaCube(:, :, i))')
%     caxis([0 2]), colormap(gca, matRad_getColormap('gammaIndex')), colorbar
%     
%     pause(2)
% end

combined = [dose dose_ann];
mAx = max(combined(:));
mIN = min(combined(:));
pass = 100 - ((nnz(gammaCube>1) * 100 )/(nnz(gammaCube>0)));
for i = 8
    ax = subplot(411);
    imagesc(squeeze(ct(:,:,i))')
    title('CT input (RSP)')
    colorbar()
    colormap(gca, 'gray')
    caxis(ax, [0, 2.5])
    
    ax1 = subplot(412);
    imagesc(squeeze(dose(:,:,i))')
    colorbar()
    colormap(gca, 'jet')
    title(['Monte Carlo Simulation [Gy] - Integral Dose = ', num2str(sum(dose(:))/1000), 'Gy'])
    ax2 = subplot(413);
    imagesc(squeeze(dose_ann(:,:,i))')
    title(['Estimated dose by ANN [Gy] - Integral Dose = ', num2str(sum(dose_ann(:))/1000), 'Gy'])
    colorbar()
    colormap(gca, 'jet')
    
    % set the colormap limit fixed for both
%     combined = [dose(:,i,:) dose_ann(:,i,:)];
%     mAx = max(combined(:));
%     mIN = min(combined(:));
    caxis(ax1, [mIN, mAx])
    caxis(ax2, [mIN, mAx])
    
    
    subplot(414)
    imagesc(squeeze(gammaCube(:, :, i))')
    title(['Gamma index analysis [\gamma] - Pass rate = ', num2str(pass) ' %'])
    caxis([0 2]), colormap(gca, matRad_getColormap('gammaIndex')), colorbar
    
    pause(1)
end
  