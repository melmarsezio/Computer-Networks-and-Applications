# COVIDSafe
#### Coursework project for Computer Networks and Applications
## Specification
In regards to problem description, input format, output messages, details are explained in [*`Assignmentv1.1.pdf`*](https://github.com/melmarsezio/Computer-Networks-and-Applications/blob/master/Assignmentv1.1.pdf)
## Instruction
##### Start-up
>+ one terminal for server with cmd `python3 server.py server_port block_duration` to run [`server.py`](https://github.com/melmarsezio/Computer-Networks-and-Applications/blob/master/server.py)
>+ many other terminals for clients with cmd `python3 client.py server_IP server_port client_udp_port` to run [`client.py`](https://github.com/melmarsezio/Computer-Networks-and-Applications/blob/master/client.py)
##### Login
>+ Client will be prompted to enter `username` and `password`
>+ three fail attempts will cause login to freeze for `block_duration` seconds.
##### Possible command
>+ `Download_tempID` will get the `tempID` for yourself
>+ `Upload_contact_log` to upload the contact history to the server
>+ `logout` to logout the client
>+ `Beacon <dest IP> <dest port>` to beacon the peers in range and exchange contact information
