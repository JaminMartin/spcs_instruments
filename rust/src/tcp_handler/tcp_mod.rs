use crate::data_handler::{sanitize_filename, Device, Entity, Experiment, ServerState};
use crossbeam::channel::Sender;
use std::io;
use std::net::SocketAddr;
use std::sync::Arc;
use std::time::Duration;
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::{TcpListener, TcpStream};
use tokio::sync::broadcast;
use tokio::sync::Mutex;
pub async fn start_tcp_server(
    tx: Sender<String>,
    addr: &str,
    state: Arc<Mutex<ServerState>>,
    mut shutdown_rx: broadcast::Receiver<()>,
) -> tokio::io::Result<()> {
    let listener = TcpListener::bind(addr).await?;
    log::info!("TCP server listening on {}", addr);

    loop {
        tokio::select! {
            Ok((socket, addr)) = listener.accept() => {
                log::info!("New connection from: {}", addr);
                let tx_clone = tx.clone();
                let state = Arc::clone(&state);
                tokio::spawn(async move {
                    handle_connection(socket, addr, tx_clone, state).await;
                });
            },
            _ = shutdown_rx.recv() => {
                log::info!("Shutdown signal received for TCP server.");
                tokio::time::sleep(Duration::from_secs(3)).await;
                drop(tx);
                break;
            }
        }
    }
    Ok(())
}

async fn handle_connection(
    socket: TcpStream,
    addr: SocketAddr,
    tx: Sender<String>,
    state: Arc<Mutex<ServerState>>,
) {
    let (reader, mut writer) = socket.into_split();
    let mut reader = BufReader::new(reader);
    let mut line = String::new();

    loop {
        line.clear();
        match reader.read_line(&mut line).await {
            Ok(0) => {
                log::info!("Connection closed by {}", addr);
                break;
            }
            Ok(_) => {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }

                match serde_json::from_str::<Device>(trimmed) {
                    Ok(device) => {
                        let device_name = device.device_name.clone();
                        let mut state = state.lock().await;
                        let entity = Entity::Device(device);
                        state.update_entity(device_name, entity);

                        if tx.send(trimmed.to_string()).is_err() {
                            log::error!("Failed to send message through channel");
                        }

                        if let Err(e) = writer.write_all(b"Device measurements recorded\n").await {
                            log::error!("Failed to send acknowledgment: {}", e);
                            break;
                        }
                    }
                    Err(_) => match serde_json::from_str::<Experiment>(trimmed) {
                        Ok(experiment) => {
                            log::info!("Experiment data processed");
                            let experiment_name = experiment.info.name.clone();
                            let mut state = state.lock().await;
                            let entity = Entity::ExperimentSetup(experiment);
                            state.update_entity(experiment_name, entity);

                            if tx.send(trimmed.to_string()).is_err() {
                                log::error!("Failed to send message through channel");
                            }

                            if let Err(e) = writer
                                .write_all(b"Experiment configuration processed\n")
                                .await
                            {
                                log::error!("Failed to send acknowledgment: {}", e);
                                break;
                            }
                        }
                        Err(e) => {
                            log::error!("Failed to parse device or experiment data: {}", e);
                            let error_msg = format!("Invalid format: {}\n", e);
                            if let Err(e) = writer.write_all(error_msg.as_bytes()).await {
                                log::error!("Failed to send error message: {}", e);
                                break;
                            }
                        }
                    },
                }
            }
            Err(e) => {
                log::error!("Error reading from {}: {}", addr, e);
                break;
            }
        }
    }
}
pub async fn save_state(
    state: Arc<Mutex<ServerState>>,
    mut shutdown_rx: broadcast::Receiver<()>,
    file_name_suffix: &str,
    output_path: &String,
) -> io::Result<()> {
    let mut interval = tokio::time::interval(Duration::from_secs(5));
    loop {
        tokio::select! {
            _ = interval.tick() => {
            let state = state.lock().await;
            let file_name = match state.get_experiment_name() {
            Some(file_name) => file_name,
            None => "".to_string()
            };

            let sanitized_file_name = sanitize_filename(file_name);

            let output_file_name = format!("{}/{}_{}.toml",output_path, sanitized_file_name, file_name_suffix);
            let _dump = state.dump_to_toml(&output_file_name);


             },
                    _ = shutdown_rx.recv() => {
            tokio::time::sleep(Duration::from_secs(3)).await;
            let mut state = state.lock().await;
            state.finalise_time();
            let file_name = match state.get_experiment_name() {
            Some(file_name) => file_name,
            None => "".to_string()
            };

            let sanitized_file_name = sanitize_filename(file_name);

            let output_file_name = format!("{}/{}_{}.toml",output_path, sanitized_file_name, file_name_suffix);
            let _dump = state.dump_to_toml(&output_file_name);


            break;
            }
        }
    }
    Ok(())
}
pub async fn server_status(
    state: Arc<Mutex<ServerState>>,
    mut shutdown_rx: broadcast::Receiver<()>,
) -> tokio::io::Result<()> {
    let mut interval = tokio::time::interval(Duration::from_secs(5));
    loop {
        tokio::select! {
                 _ = interval.tick() => {
                let state = state.lock().await;
                state.print_state();
            },
            _ = shutdown_rx.recv() => {
            tokio::time::sleep(Duration::from_secs(3)).await;
            break;
            }
        }
    }

    Ok(())
}
