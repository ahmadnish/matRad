% Here I write codes such as in nish_scribbles, with the difference 
% that the code here I can track it via git, the other is just fast check 


load('C:\matRad\nishTopas\losses\loss_RNN_BOX.mat')

figure
set(gcf, 'color', 'w')
set(gcf, 'Units', 'Normalized', 'OuterPosition', [0.1, 0.1, .5, .7]);

ax1 = subplot(211);
h11 = plot(mean(loss_train, 2), 'LineWidth', 2);
hold on
h12 = plot(mean(loss_test, 2), 'LineWidth', 2);

lg1 = legend('Train loss', 'Test loss');
lg1.FontName = 'Times New Roman';
lg1.FontSize = 18;

ax1.XAxis.FontName = 'Times New Roman';
ax1.XAxis.FontSize = 20;
ax1.YAxis.FontName = 'Times New Roman';
ax1.YAxis.FontSize = 20;
ax1.YAxis.Exponent = -3;

xlabel('Epochs (#)', 'FontName', 'Times New Roman', 'FontSize', 20, 'FontWeight', 'normal')
ylabel ('MSE', 'FontName', 'Times New Roman', 'FontSize', 20, 'FontWeight', 'normal')

%%
load('C:\matRad\nishTopas\losses\loss_LSTM_BOX.mat')

ax2 = subplot(212);

h21 = plot(mean(loss_train, 2), 'LineWidth', 2);
hold on
h22 = plot(mean(loss_test, 2), 'LineWidth', 2);

ax2.XAxis.FontName = 'Times New Roman';
ax2.XAxis.FontSize = 22;
ax2.YAxis.FontName = 'Times New Roman';
ax2.YAxis.FontSize = 22;

xlabel('Epochs (#)', 'FontName', 'Times New Roman', 'FontSize', 20, 'FontWeight', 'normal')
ylabel ('MSE', 'FontName', 'Times New Roman', 'FontSize', 20, 'FontWeight', 'normal')

lg2 = legend('Train loss', 'Test loss');
lg2.FontName = 'Times New Roman';
lg2.FontSize = 18;

ax2.YLabel.Position(1) = ax1.YLabel.Position(1);