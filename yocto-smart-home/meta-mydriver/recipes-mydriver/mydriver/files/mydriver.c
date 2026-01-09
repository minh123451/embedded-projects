#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/i2c.h>
#include <linux/init.h>
#include <linux/slab.h>
#include <linux/fs.h>
#include <linux/uaccess.h>

static struct i2c_device_id mydriver_id[] = {
    { "mydriver", 0 },
    { }
};

MODULE_DEVICE_TABLE(i2c, mydriver_id);

static int major_number;
static struct class *mydriver_class = NULL;
static struct device *mydriver_device = NULL;

static struct i2c_client *my_client = NULL;

#define DEVICE_NAME "mydriver_device"
#define BUFFER_SIZE 128

static char buffer[BUFFER_SIZE] = { 0 };

// Open device file
static int mydriver_open(struct inode *inode, struct file *file)
{
    pr_info("MyDriver: Device opened\n");
    return 0;
}

// Close device file
static int mydriver_release(struct inode *inode, struct file *file)
{
    pr_info("MyDriver: Device closed\n");
    return 0;
}

// Read from device file
static ssize_t mydriver_read(struct file *file, char __user *user_buffer, size_t len, loff_t *offset)
{
    int ret;
    pr_info("MyDriver: Reading from device\n");

    if (!my_client) {
        pr_err("MyDriver: I2C client not initialized\n");
        return -ENODEV;
    }

    if (len > BUFFER_SIZE) len = BUFFER_SIZE; // Limit the size of read operations

    // Receive data from the I2C slave
    ret = i2c_master_recv(my_client, buffer, len);
    if (ret < 0) {
        pr_err("MyDriver: I2C read failed\n");
        return ret;
    }

    // Copy data to user space
    if (copy_to_user(user_buffer, buffer, len)) {
        return -EFAULT;
    }

    pr_info("MyDriver: Read %ld bytes from I2C slave\n", len);
    return len;
}

// Write to device file - Truyền dữ liệu qua I2C
static ssize_t mydriver_write(struct file *file, const char __user *user_buffer, size_t len, loff_t *offset)
{
    pr_info("MyDriver: Writing to device\n");

    if (!my_client) {
        pr_err("MyDriver: I2C client not initialized\n");
        return -ENODEV;
    }

    if (len > BUFFER_SIZE) len = BUFFER_SIZE; // Limit the size of write operations

    // Copy data from user space
    if (copy_from_user(buffer, user_buffer, len)) {
        return -EFAULT;
    }

    // Send data to the I2C slave
    int ret = i2c_master_send(my_client, buffer, len); 
    // Send 'len' bytes from buffer to the I2C slave
        if (ret < 0) {
            pr_err("MyDriver: I2C write failed\n");
            return ret;  // Return error code if the write operation fails
        }

    pr_info("MyDriver: Wrote %ld bytes to I2C slave\n", len);
    return len;
}
static struct file_operations fops = {
    .open = mydriver_open,
    .release = mydriver_release,
    .read = mydriver_read,
    .write = mydriver_write,
};

// Probe function
static int mydriver_probe(struct i2c_client *client, const struct i2c_device_id *id)
{
    pr_info("MyDriver: Device detected at 0x%02x\n", client->addr);
    my_client = client;

    // Register character device
    major_number = register_chrdev(0, DEVICE_NAME, &fops);
    if (major_number < 0) {
        pr_err("MyDriver: Failed to register a major number\n");
        return major_number;
    }

    // Create device class
    mydriver_class = class_create(THIS_MODULE, "mydriver_class");
    if (IS_ERR(mydriver_class)) {
        unregister_chrdev(major_number, DEVICE_NAME);
        pr_err("MyDriver: Failed to create device class\n");
        return PTR_ERR(mydriver_class);
    }

    // Create device node
    mydriver_device = device_create(mydriver_class, NULL, MKDEV(major_number, 0), NULL, DEVICE_NAME);
    if (IS_ERR(mydriver_device)) {
        class_destroy(mydriver_class);
        unregister_chrdev(major_number, DEVICE_NAME);
        pr_err("MyDriver: Failed to create device\n");
        return PTR_ERR(mydriver_device);
    }

    return 0;
}

// Remove function
static int mydriver_remove(struct i2c_client *client)
{
    pr_info("MyDriver: Device removed\n");

    // Clean up
    device_destroy(mydriver_class, MKDEV(major_number, 0));
    class_unregister(mydriver_class);
    class_destroy(mydriver_class);
    unregister_chrdev(major_number, DEVICE_NAME);

    return 0;
}

static struct i2c_driver mydriver_driver = {
    .driver = {
        .name = "mydriver",
        .owner = THIS_MODULE,
    },
    .probe = mydriver_probe,
    .remove = mydriver_remove,
    .id_table = mydriver_id,
};

static int __init mydriver_init(void)
{
    return i2c_add_driver(&mydriver_driver);
}

static void __exit mydriver_exit(void)
{
    i2c_del_driver(&mydriver_driver);
}

module_init(mydriver_init);
module_exit(mydriver_exit);

MODULE_LICENSE("GPL");
MODULE_AUTHOR("DANG VAN NGUYEN");
MODULE_DESCRIPTION("This is a driver i2c interface with one ditail devices");
