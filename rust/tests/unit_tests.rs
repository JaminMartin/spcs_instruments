// tests/basic_test.rs

use crossbeam::channel;
use regex::Regex;
use spcs_rust_utils::data_handler::*;
use spcs_rust_utils::tcp_handler::*;
use std::collections::HashMap;
use std::net::SocketAddr;
use std::sync::Arc;
use tokio::io::AsyncWriteExt;
use tokio::net::TcpStream;
use tokio::sync::broadcast;
use tokio::sync::Mutex;

use std::thread;

use tokio::io::AsyncReadExt;

async fn send_test_device_data(addr: SocketAddr) -> tokio::io::Result<()> {
    println!("Attempting to connect to {}", addr);
    let mut stream = TcpStream::connect(addr).await?;
    println!("Successfully connected to server");
    let test_device = Device {
        device_name: "test_device".to_string(),
        device_config: HashMap::new(),
        measurements: HashMap::new(),
    };
    let json = serde_json::to_string(&test_device).unwrap();
    println!("Sending data to server: {}", json);

    stream.write_all(format!("{}\n", json).as_bytes()).await?;
    stream.flush().await?;
    println!("Data sent successfully");

    println!("Waiting for server response...");
    let mut buffer = [0u8; 1024];
    match stream.read(&mut buffer).await {
        Ok(n) if n > 0 => {
            let response = String::from_utf8_lossy(&buffer[..n]);
            println!("Received {} bytes from server", n);
            println!("Raw response: {:?}", response);
            let trimmed = response.trim();
            println!("Trimmed response: {:?}", trimmed);
            assert!(
                trimmed == "Device measurements recorded",
                "Unexpected response: {:?}",
                trimmed
            );
        }
        Ok(n) => {
            eprintln!("Empty response received (bytes: {})", n);
            return Err(std::io::Error::new(
                std::io::ErrorKind::Other,
                "Empty response",
            ));
        }
        Err(e) => {
            eprintln!("Error reading response: {}", e);
            return Err(e);
        }
    };

    Ok(())
}

#[test]
fn test_tcp_server_basic_connection() {
    let state = Arc::new(Mutex::new(ServerState::default()));
    let (shutdown_tx, shutdown_rx) = broadcast::channel(1);
    let (msg_tx, _msg_rx) = channel::unbounded();
    let addr = "127.0.0.1:8080";
    let shutdown_tx_clone = shutdown_tx.clone();
    let tcp_server_thread = thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(start_tcp_server(msg_tx, addr, state, shutdown_rx, shutdown_tx_clone))
            .unwrap();
    });

    std::thread::sleep(std::time::Duration::from_secs(1));

    let addr: SocketAddr = addr.parse().unwrap();
    let tcp_client_thread = thread::spawn(move || {
        let rt = tokio::runtime::Runtime::new().unwrap();
        rt.block_on(send_test_device_data(addr))
    });

    std::thread::sleep(std::time::Duration::from_secs(5));

    shutdown_tx.send(()).unwrap();
    tcp_server_thread.join().unwrap();
    let client_result = tcp_client_thread.join().unwrap();

    assert!(client_result.is_ok(), "this should pass based on data sent");
}
#[test]
fn test_create_time_stamp() {
    let timestamp = create_time_stamp(false);
    let re = Regex::new(r"^\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2}\.\d{3}$").unwrap();
    assert!(
        re.is_match(&timestamp),
        "Timestamp does not match expected format: {}",
        timestamp
    );

    let header_timestamp = create_time_stamp(true);
    let header_re = Regex::new(r"^\d{2}_\d{2}_\d{4}_\d{2}_\d{2}_\d{2}_\d{3}$").unwrap();
    assert!(
        header_re.is_match(&header_timestamp),
        "Header timestamp does not match expected format: {}",
        header_timestamp
    );
}

#[test]
fn test_sanitize_filename() {
    assert_eq!(sanitize_filename("file name".to_string()), "file_name");

    assert_eq!(sanitize_filename("file/name".to_string()), "file_name");

    assert_eq!(sanitize_filename("file / name".to_string()), "file___name");

    assert_eq!(sanitize_filename("filename".to_string()), "filename");

    assert_eq!(
        sanitize_filename("file / name / test".to_string()),
        "file___name___test"
    );
}

#[test]
fn test_load_data() {
    // Write a sample TOML string for testing
    let toml_content = r#"[device.Test_DAQ.data]
counts = [778.2368218901281, 6377.393470601288, 2316.8743649537096]
voltage = [778.2368218901281, 6377.393470601288, 2316.8743649537096]
trace = [[1.1,2.2,3.3],[4.4,5.5,6.6],[7.7,8.8,9.9],[10.0,11.1, 12.2]]
"#;
    let temp_file = "test_data.toml";
    std::fs::write(temp_file, toml_content).expect("Failed to write temporary TOML file");

    let data = load_experimental_data(temp_file);
    std::fs::remove_file(temp_file).expect("Failed to delete temporary TOML file");

    assert!(
        data.contains_key("Test_DAQ"),
        "Test_DAQ section not found in the data"
    );
    let test_daq_data = data.get("Test_DAQ").expect("Missing Test_DAQ section");

    let counts = test_daq_data.get("counts").expect("Missing counts data");
    match counts {
        MeasurementData::Single(values) => assert_eq!(
            values,
            &vec![778.2368218901281, 6377.393470601288, 2316.8743649537096]
        ),
        _ => panic!("Unexpected data format for counts"),
    }

    let voltage = test_daq_data.get("voltage").expect("Missing voltage data");
    match voltage {
        MeasurementData::Single(values) => assert_eq!(
            values,
            &vec![778.2368218901281, 6377.393470601288, 2316.8743649537096]
        ),
        _ => panic!("Unexpected data format for voltage"),
    }
    let trace = test_daq_data.get("trace").expect("Missing voltage data");
    match trace {
        MeasurementData::Multi(values) => assert_eq!(
            values,
            &vec![vec![1.1,2.2,3.3],vec![4.4,5.5,6.6],vec![7.7,8.8,9.9],vec![10.0,11.1, 12.2]]
        ),
        _ => panic!("Unexpected data format for voltage"),
    }
}
