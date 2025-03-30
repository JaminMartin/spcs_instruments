use crate::data_handler::{sanitize_filename, Device, Entity, Experiment, ServerState, Listner};
use crossbeam::channel::Sender;
use std::io;
use std::net::SocketAddr;
use std::path::MAIN_SEPARATOR;
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
    shutdown_tx: broadcast::Sender<()>
) -> tokio::io::Result<()> {
    let listener = TcpListener::bind(addr).await?;
    log::info!("TCP server listening on {}", addr);

    loop {
        tokio::select! {
            Ok((socket, addr)) = listener.accept() => {
                log::debug!("New connection from: {}", addr);
                let tx_clone = tx.clone();
                let shutdown_tx = shutdown_tx.clone();
                let state = Arc::clone(&state);
                tokio::spawn(async move {
                    handle_connection(socket, addr, tx_clone, state, shutdown_tx).await;
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
    shutdown_tx: broadcast::Sender<()>
) {
    let (reader, mut writer) = socket.into_split();
    let mut reader = BufReader::new(reader);
    let mut line = String::new();

    loop {
        line.clear();
        match reader.read_line(&mut line).await {
            Ok(0) => {
                log::debug!("Connection closed by {}", addr);
                break;
            }
            Ok(_) => {
                let trimmed = line.trim();
                if trimmed.is_empty() {
                    continue;
                }
                match trimmed {
                "GET_DATASTREAM" => {
                        let state = state.lock().await;
                        let steam_data = state.send_stream();
                        match serde_json::to_string(&steam_data) {
                            Ok(state_json) => {
                                if let Err(e) = writer
                                    .write_all(format!("{}\n", state_json).as_bytes())
                                    .await
                                {
                                    log::error!("Failed to send server state: {}", e);
                                    break;
                                }
                                continue;
                            }
                            Err(e) => {
                                log::error!("Failed to serialize server state: {}", e);
                                if let Err(e) =
                                    writer.write_all(b"Error serializing server state\n").await
                                {
                                    log::error!("Failed to send error message: {}", e);
                                    break;
                                }
                                continue;
                            }
                        }
                    }

                "PAUSE_STATE" => {
                    if let Err(e) = writer
                                    .write_all(format!("Setting internal server state to paused...\n").as_bytes())
                                    .await
                                    
                                {
                                    log::error!("Failed to send server state: {}", e);
                                    break;
                                }
                                let mut state = state.lock().await; 
                                state.internal_state = false;
                                log::info!("setting server state to paused....");
                                continue;   
                            }

                "KILL" => {
                    if let Err(e) = writer
                                    .write_all(format!("Shutting down server...\n").as_bytes())
                                    .await
                                    
                                    //kill the process
                                {
                                    log::error!("Failed to send server state: {}", e);
                                    break;
                                }
                                log::info!("Recieved remote termination command, shutting down server"); 
                                let _ = shutdown_tx.send(());
                                break   
                            } 
                "RESUME_STATE" => {
                    if let Err(e) = writer
                                    .write_all(format!("Setting internal server state to start...\n").as_bytes())
                                    .await
                                {
                                    log::error!("Failed to send server state: {}", e);
                                    break;
                                }
                                let mut state = state.lock().await; 
                                state.internal_state = true;
                                continue;   
                                
                            }            
                _ => {}    



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
                        Err(_) => match serde_json::from_str::<Listner>(trimmed) {
                            Ok(_) => {
                                log::debug!("Listner querry");
                                let state = state.lock().await;
                                if tx.send(trimmed.to_string()).is_err() {
                                    log::error!("Failed to send message through channel");
                                }   
                                if state.internal_state == true {
                                    if let Err(e) = writer
                                    .write_all(b"Running\n")
                                    .await
                                {
                                    log::error!("Failed to send acknowledgment: {}", e);
                                    break;
                                }
                                } else {

                                    if let Err(e) = writer
                                    .write_all(b"Paused\n")
                                    .await
                                {
                                    log::error!("Failed to send acknowledgment: {}", e);
                                    break;
                                }

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
) -> io::Result<String> {
    let mut interval = tokio::time::interval(Duration::from_secs(3));
    tokio::time::sleep(Duration::from_secs(1)).await;
    let mut output_file_name = String::new();
    let _ = output_file_name;
    loop {
        tokio::select! {
            _ = interval.tick() => {
                let mut retries = 3;
                while retries > 0 {
                    {
                        let state_guard = state.lock().await;
                        if let Err(err) = state_guard.validate() {
                            log::warn!("Validation failed: {:?}. Retrying in 5 seconds...", err);
                            retries -= 1;
                            if retries == 0 {
                                return Err(io::Error::new(
                                    io::ErrorKind::InvalidData,
                                    format!("State is invalid after retry: {:?}", err),
                                ));
                            }
                        } else {
                            let file_name = match state_guard.get_experiment_name() {
                                Some(name) => name,
                                None => "".to_string(),
                            };
                            let sanitized_file_name = sanitize_filename(file_name);
                            let sanitized_output_path = clean_trailing_slash(output_path);
                            output_file_name = format_file_path(&sanitized_output_path, &sanitized_file_name, &file_name_suffix);

                            state_guard.dump_to_toml(&output_file_name)?;
                            break;
                        }
                    }
                    tokio::time::sleep(Duration::from_secs(5)).await;
                }
            }
            _ = shutdown_rx.recv() => {
                tokio::time::sleep(Duration::from_secs(3)).await;
                let mut state = state.lock().await;
                state.finalise_time();
                let file_name = match state.get_experiment_name() {
                    Some(file_name) => file_name,
                    None => "".to_string()
                };
                let sanitized_file_name = sanitize_filename(file_name);
                let sanitized_output_path = clean_trailing_slash(output_path);
                output_file_name = format_file_path(&sanitized_output_path, &sanitized_file_name, &file_name_suffix);
                state.dump_to_toml(&output_file_name)?;
                break;
            }
        }
    }
    log::info!("Saved state to: {}", output_file_name);
    Ok(output_file_name)
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

pub fn clean_trailing_slash(path: &str) -> String {
    path.trim_end_matches(|c| c == '/' || c == '\\').to_string()
}

fn format_file_path(output_path: &str, file_name: &str, file_suffix: &str) -> String {
    let sanitized_output_path = clean_trailing_slash(output_path);
    let separator = MAIN_SEPARATOR;
    format!("{sanitized_output_path}{separator}{file_name}_{file_suffix}.toml")
}
