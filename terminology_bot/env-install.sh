#!/bin/bash
# packages installation for Ubuntu. Checked on Ubuntu 18.04

sudo apt-get update -y
sudo apt-get install docker.io python3-pip -y
sudo usermod -aG docker $USER
