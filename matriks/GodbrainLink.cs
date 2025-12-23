using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using Matriks.Data.Symbol;
using Matriks.Engines;
using Matriks.Indicators;
using Matriks.Symbols;
using Matriks.AlgoTrader;
using Matriks.Trader.Core;
using Matriks.Trader.Core.Fields;
using System.Net;
using System.Net.Sockets;

// GODBRAIN NEURAL LINK - TRANSMITTER V1.0
// PURPOSE: Relays real-time tick data from Matriks to Python Core
// PROTOCOL: TCP/IP Socket to localhost:5000
namespace Matriks.Lean.Algotrader
{
    public class GodbrainLink : MatriksAlgo
    {
        // Configuration - Symbol to track
        [SymbolParameter("GARAN")]
        public string Symbol = "GARAN";

        [Parameter(SymbolPeriod.Min1)]
        public SymbolPeriod Period = SymbolPeriod.Min1;

        // Socket Connection Details
        private Socket sender;
        private string ipAddress = "127.0.0.1"; // Localhost
        private int port = 5000; // The port GODBRAIN is listening on
        private bool isConnected = false;
        private int reconnectAttempts = 0;
        private const int MAX_RECONNECT = 5;

        public override void OnInit()
        {
            AddSymbol(Symbol, Period);

            // Establish Connection to GODBRAIN
            ConnectToCore();
            
            Debug("GODBRAIN Link Initialized for: " + Symbol);
        }

        public void ConnectToCore()
        {
            try 
            {
                IPAddress ip = IPAddress.Parse(ipAddress);
                IPEndPoint remoteEP = new IPEndPoint(ip, port);

                sender = new Socket(ip.AddressFamily, SocketType.Stream, ProtocolType.Tcp);
                sender.Connect(remoteEP);
                isConnected = true;
                reconnectAttempts = 0;
                Debug("CONNECTION ESTABLISHED: Linked to Godbrain Core.");
            } 
            catch (Exception e) 
            {
                isConnected = false;
                Debug("CONNECTION FAILED: " + e.Message);
            }
        }

        public void TryReconnect()
        {
            if (reconnectAttempts < MAX_RECONNECT)
            {
                reconnectAttempts++;
                Debug("RECONNECTING... Attempt " + reconnectAttempts);
                System.Threading.Thread.Sleep(1000); // Wait 1 second
                ConnectToCore();
            }
        }

        public override void OnDataUpdate(BarDataEventArgs barData)
        {
            if (!isConnected) 
            {
                TryReconnect();
                return;
            }

            // Prepare the Data Packet (JSON format)
            // Structure: {"symbol": "GARAN", "price": 10.50, "time": "10:30:00", "volume": 1000}
            
            var closes = barData.BarData.Close;
            var volumes = barData.BarData.Volume;
            
            if (closes.Count == 0) return;
            
            var currentClose = closes[closes.Count - 1];
            var currentVolume = volumes.Count > 0 ? volumes[volumes.Count - 1] : 0;
            var currentTime = DateTime.Now.ToString("HH:mm:ss");

            string jsonPayload = String.Format(
                "{{\"symbol\": \"{0}\", \"price\": {1}, \"time\": \"{2}\", \"volume\": {3}}}", 
                Symbol, 
                currentClose.ToString(System.Globalization.CultureInfo.InvariantCulture), 
                currentTime,
                currentVolume.ToString(System.Globalization.CultureInfo.InvariantCulture)
            );

            SendData(jsonPayload);
        }

        public void SendData(string message)
        {
            try
            {
                byte[] msg = Encoding.ASCII.GetBytes(message);
                int bytesSent = sender.Send(msg);
                // Debug("Sent: " + message); // Uncomment for verbose logging
            }
            catch (Exception e)
            {
                Debug("TRANSMISSION ERROR: " + e.Message);
                isConnected = false;
            }
        }

        public override void OnStop()
        {
            if (sender != null)
            {
                try
                {
                    sender.Shutdown(SocketShutdown.Both);
                    sender.Close();
                }
                catch (Exception e)
                {
                    Debug("Cleanup error: " + e.Message);
                }
            }
            Debug("GODBRAIN LINK TERMINATED.");
        }
    }
}
