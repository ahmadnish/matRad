dose = resultGUI.physicalDose(40:119, 66:94, 66:94);
ct_tmp = ct.cube{1}(40:119, 66:94, 66:94);
filename = 'presentation.gif';
h = figure('units','normalized','outerposition',[0 0 1 1])
figtitle = sgtitle('an')
for i = 1:60
    newtitle = ['Plane number: ', num2str(i)];
    figtitle.String = newtitle;
    figtitle.FontSize = 36;
    subplot(121)
    imshow(squeeze(ct_tmp(i, :,:)),'DisplayRange', [1 2.5], 'colormap', colormap('jet'))
    colorbar
    subplot(122)
    imshow(squeeze(dose(i,:,:)),'DisplayRange', [0, 0.08], 'colormap', colormap('jet'))
    colorbar
%     p = .3;
%     if i>47
%         p = .03;
%     end
%     pause(p)
    frame = getframe(h);
    imm = frame2im(frame);
    [imbind, cm] = rgb2ind(imm, 256);
    % Write to the GIF File
    if i == 1
        imwrite(imbind, cm, filename,'gif', 'Loopcount', 1, 'DelayTime', .3);
    else
        imwrite(imbind, cm, filename,'gif','WriteMode','append', 'DelayTime', .3);
    end
end
