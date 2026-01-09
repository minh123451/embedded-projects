#include "mainwindow.h"
#include "ui_mainwindow.h"
#include <QTimer>
#include <QDebug>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#define I2C_DEV_PATH "/dev/i2c-1"  // address driveri2csystem
#define GPIO_DEV_PATH "/dev/gpio_device"
#define SLAVE_ADDR 0x20

MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , ui(new Ui::MainWindow)
{
    ui->setupUi(this);


    i2cFd = open(I2C_DEV_PATH, O_RDWR);
    if (i2cFd < 0) {
        qCritical() << "Error opening I2C Bus";
        exit(1);
    }

    if (ioctl(i2cFd, I2C_SLAVE, SLAVE_ADDR) < 0) {
        qCritical() << "Error setting slave address";
        exit(1);
    }

    gpioFd = open(GPIO_DEV_PATH, O_RDWR);
    if (gpioFd < 0) {
        qCritical() << "Error opening gpio_device";
        exit(1);
    }

    connect(ui->BT1, &QPushButton::clicked, this, &MainWindow::on_BT1_clicked);
    connect(ui->BT2, &QPushButton::clicked, this, &MainWindow::on_BT2_clicked);
    connect(ui->BT3, &QPushButton::clicked, this, &MainWindow::on_BT3_clicked);
    connect(ui->BT4, &QPushButton::clicked, this, &MainWindow::on_BT4_clicked);

    QTimer *timer = new QTimer(this);
    connect(timer, &QTimer::timeout, this, &MainWindow::updateLedStatus);
    timer->start(500);
}

MainWindow::~MainWindow()
{

    ::close(i2cFd);
    delete ui;
}

QByteArray MainWindow::readI2CState() {
    QByteArray data(4, 0);
    ssize_t bytesRead = read(i2cFd, data.data(), 4);
    if (bytesRead < 0) {
        qWarning() << "Error reading from I2C:" << strerror(errno);
        return QByteArray();
        }
    else if (bytesRead != 4) {
        qWarning() << "Incomplete read, expected 4 bytes but got" << bytesRead;
        }
    return data;
}
void MainWindow::sendI2CCommand(uint8_t command) {
    if (i2cFd < 0) {
        qWarning() << "Error: I2C file descriptor is invalid.";
        return;
    }

    ssize_t bytesWritten = write(i2cFd, &command, 1);
    if (bytesWritten < 0) {
        perror("Error writing to I2C device");
    } else if (bytesWritten != 1) {
        qWarning() << "Warning: Partial write to I2C device. Bytes written:" << bytesWritten;
    }
}

void MainWindow::on_BT1_clicked()
{
    if(ui->BT1->styleSheet() == "background-color: rgb(98, 160, 234);")
        sendI2CCommand(0x01);//tat thiet bi 1
    else
        sendI2CCommand(0x02);//bat thiet bi 1

}


void MainWindow::on_BT2_clicked()
{
    if(ui->BT2->styleSheet() == "background-color: rgb(98, 160, 234);")
        sendI2CCommand(0x03);//tat thiet bi 2
    else
        sendI2CCommand(0x04);//bat thiet bi 2

}


void MainWindow::on_BT3_clicked()
{
    if(ui->BT3->styleSheet() == "background-color: rgb(98, 160, 234);")
        sendI2CCommand(0x05);//tat thiet bi 3
    else
        sendI2CCommand(0x06);//bat thiet bi 3

}


void MainWindow::on_BT4_clicked()
{
    if(ui->BT4->styleSheet() == "background-color: rgb(98, 160, 234);"){
        ssize_t bytesWrittens = write(gpioFd, "1", 1);
        if (bytesWrittens < 0) {
            perror("Error writing to gpio_device");
        }
        else if (bytesWrittens != 1) {
        qWarning() << "Warning: just write one byte to gpio_device. Bytes written:" << bytesWrittens;
        }
    }
    else {
        ssize_t bytesWrittens = write(gpioFd, "0", 1);
        if (bytesWrittens < 0) {
            perror("Error writing to gpio_device");
        }
        else if (bytesWrittens != 1) {
        qWarning() << "Warning: just write one byte to gpio_device. Bytes written:" << bytesWrittens;
        }
    }

}

void MainWindow::updateLedStatus() {
    char buffer;
    ssize_t bytesRead = read(gpioFd, &buffer, sizeof(buffer));
    if (bytesRead < 0) {
        perror("Error read to gpio_device");
    }
    else if (bytesRead != 1) {
        qWarning() << "Warning: just write one byte to gpio_device. Bytes written:" << bytesRead;
    }
    QByteArray state = readI2CState();
    if (state.size() < 3) {
        qWarning() << "Error: Incomplete state data from I2C";
        return;
    }
    // cap nhat trang thai tra ve
    ui->BT1->setStyleSheet(state[0] ? "background-color: rgb(98, 160, 234);" : "background-color: rgb(237, 51, 59);");
    ui->BT2->setStyleSheet(state[1] ? "background-color: rgb(98, 160, 234);" : "background-color: rgb(237, 51, 59);");
    ui->BT3->setStyleSheet(state[2] ? "background-color: rgb(98, 160, 234);" : "background-color: rgb(237, 51, 59);");
    ui->BT4->setStyleSheet(buffer ? "background-color: rgb(98, 160, 234);" : "background-color: rgb(237, 51, 59);");
}

