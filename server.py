import asyncio
import aiohttp
import json
import logging
import time
import argparse

servers = ["Hill", "Jaquez", "Smith", "Campbell", "Singleton"]

port_num = {
    "Hill":11625,
    "Jaquez":11626,
    "Smith":11627,
    "Campbell":11628,
    "Singleton":11629,
}

nw_communication= {
    "Hill": ["Jaquez","Smith"],
    "Jaquez": ["Hill","Singleton"], 
    "Smith": ["Campbell","Hill","Singleton"],
    "Campbell": ["Singleton","Smith"],
    "Singleton": ["Jaquez","Smith", "Campbell"]
}

API_KEY='AIzaSyAlWDLjO3zgJuXeh8yTM6jV1RRRTd_ZRSQ' #key

class Server:
    def __init__(self, name, ip, port):
        self.name = name
        self.ip = ip
        self.port = port
        self.timestamp=dict()
        self.message=dict()


    async def handle_input(self, reader, writer):
        """
        on server side
        """
        encoded_data = await reader.read(1000)
        message_received = encoded_data.decode()
        time_now = time.time()
        print("{} received {}".format(self.name, message_received))

        message_array = message_received.split()
        sendback_message=""
        if ((len(message_array)==4 and (message_array[0]=="IAMAT" or message_array[0]=="WHATSAT")) or (len(message_array)==6 and message_array[0]=="AT")):
            if message_array[0]=="IAMAT":
                print("here1")
                coord = message_array[2]
                len_coord = len(coord)
                result_arr = []

                for i in range (len_coord):
                    if coord[i]=="+":
                        result_arr.append(i)
                    elif coord[i]=="-":
                        result_arr.append(i)
                if len(result_arr)!=2:
                    print("here2")
                    sendback_message = '? ' + message_received
                    pass
                last_index = len_coord-1
                if coord[0]== "+" or coord[0]== "-" and coord[last_index].isdigit():

                    #  VALID IAMAT message here

                    sendback_message = await self.IAMAT_func(message_array,time_now)
                    logging.info("{} sent: {}".format(self.name, sendback_message))
            elif message_array[0]=="WHATSAT":
                radius= int(message_array[2])
                upp_bound= int(message_array[3])
                if radius >0 and radius<=50 and upp_bound>0 and upp_bound<=20:
                    sendback_message = await self.WHATSAT_func(message_array)   
                else: 
                    sendback_message = '? ' + message_received
 
            elif message_array[0]=="AT":
                await self.AT_func(message_array)
                sendback_message=""

            else:
                sendback_message = '? ' + message_received

        print("{} send: {}".format(self.name, sendback_message))
        logging.info("{} send: {}".format(self.name, sendback_message))
        writer.write(sendback_message.encode())
        await writer.drain()
        print("close the client socket")
        writer.close()

    async def run_forever(self):
        server = await asyncio.start_server(self.handle_input, self.ip, self.port)

        # Serve requests until Ctrl+C is pressed
        async with server:
            await server.serve_forever()
        # Close the server
        server.close()



    async def WHATSAT_func(self,message_array):
                
        id = message_array[1]
        radius=message_array[2]
        upp_bound=message_array[3]


        self_message_arry = self.message[id].split()
#        message_str = "{} {} {} {} {} {}".format(self_message_arry[0],self_message_arry[1],self_message_arry[2],self_message_arry[3],self_message_arry[4],self_message_arry[5])


        coord = self_message_arry[4]
        print("coord is "+ coord)
        if id not in self.message:
            sendback_message = "? {} {} {} {}".format(message_array[0],id,radius,upp_bound)
            return sendback_message

        location = filter_coord(coord)
        location = location[0] + "," + location[1]
        radius_m = str(float(radius)*1000)

        url = 'https://maps.googleapis.com/maps/api/place/nearbysearch/json?location={}&radius={}&key={}'.format(location,radius_m,API_KEY)
        sendback_message = self.message[id]
        print("sendback message is: " + sendback_message)
        server_response = sendback_message +"\n"

        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(
            ssl=False),) as session:
            async with session.get(url) as resp:
                response = await resp.json()

            response["results"] = response["results"][:int(upp_bound)]
            url_out = json.dumps(response, indent=3)

        return server_response + url_out + "\n\n"

    async def IAMAT_func(self,message_array,time_now):
        id = message_array[1]
        coordinates = message_array[2]
        timestamp = message_array[3]
        print("client_timestamp is:" + timestamp)
        print("server:" + str(time_now))
        time_diff = float(time_now)- float(timestamp)
        if time_diff>0:
            time_diff = '+' + str(time_diff)
        time_diff=str(time_diff)
        sendback_message = "AT {} {} {} {} {}".format(self.name, time_diff, id, coordinates, timestamp)
        self.timestamp[id]=timestamp
        self.message[id]=sendback_message

        await self.flood(sendback_message)

        return sendback_message

    async def AT_func(self,message_array):
        id = message_array[3]
        timestamp = message_array[5]
        message_str = "{} {} {} {} {} {}".format(message_array[0],message_array[1],message_array[2],message_array[3],message_array[4],message_array[5])
        if id in self.message:
            if timestamp>self.timestamp[id]:
                self.timestamp[id]=timestamp
                self.message[id]=message_str
                await self.flood(message_str)
        else:
                self.timestamp[id]=timestamp
                self.message[id]=message_str # str/ array
                await self.flood(message_str)


    async def flood(self,msg):
         for s in nw_communication[self.name]:
             try:
                 reader,writer = await asyncio.open_connection('127.0.0.1',port_num[s])
                 writer.write(msg.encode()) #write message to all connected network
                 logging.info("{} send: {}".format(self.name, msg)) 
                 await writer.drain()
                 print("close the client socket")
                 writer.close()
                 await writer.wait_closed()
             except:
                 print("fail to connect to server: " + s)
                 pass

def filter_coord(coord):
    position=[]
    print("coordinate string is: "+coord)
    for i in range (len(coord)):
        if coord[i]== "+":
            position.append(i)
        elif coord[i]=="-":
            position.append(i)

    coord_1 = coord[1:position[1]]
    coord_2 = coord[position[1]:len(coord)-1]
    return [coord_1,coord_2]


def main():
    parser = argparse.ArgumentParser('CS131 project example argument parser')
    parser.add_argument('server_name', type=str, help='required server name input')
    args = parser.parse_args()

    print("Hello, welcome to server {}".format(args.server_name))

    server = Server(args.server_name, '127.0.0.1', port_num[args.server_name])
    logging.basicConfig(filename=args.server_name + "-log", format='%(name)s - %(levelname)s - %(message)s',filemode='w',level=logging.INFO)

    try:
        asyncio.run(server.run_forever())
    except KeyboardInterrupt:
        pass


if __name__ == '__main__':
    main()



