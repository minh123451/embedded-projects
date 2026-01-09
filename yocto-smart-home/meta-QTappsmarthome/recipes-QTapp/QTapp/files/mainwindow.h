#ifndef MAINWINDOW_H
#define MAINWINDOW_H

#include <QMainWindow>

QT_BEGIN_NAMESPACE
namespace Ui { class MainWindow; }
QT_END_NAMESPACE

class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

private slots:
    void on_BT1_clicked();

    void on_BT2_clicked();

    void on_BT3_clicked();

    void on_BT4_clicked();

    void updateLedStatus();

    void on_pushButton_4_clicked();

private:
    Ui::MainWindow *ui;
    int gpioFd;
    int i2cFd;
    void sendI2CCommand(uint8_t command);
    QByteArray readI2CState();
};
#endif // MAINWINDOW_H
