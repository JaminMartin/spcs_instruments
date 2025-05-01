use crate::data_handler::get_configuration;
use lettre::message::{header::ContentType, Attachment, MultiPart, SinglePart};
use lettre::transport::smtp::authentication::Credentials;
use lettre::{Message, SmtpTransport, Transport};
use std::fs;
pub fn mailer(email_adr: Option<&String>, file_path: &String) {
    if let Some(email) = email_adr {
        let email_configuration = match get_configuration() {
            Ok(conf) => match conf.email_server {
                Some(email) => email,
                None => {
                    log::error!("failed to get email configuration as it could not be found, have you configured the email server?");
                    return;
                }
            },
            Err(e) => {
                log::error!("failed to get configuration due to: {}", e);
                return;
            }
        };
        let filename = get_filename_from_path(&file_path);
        let filebody = fs::read(file_path).expect("Cant find file!");
        let content_type = ContentType::parse("text/plain").unwrap();
        let attachment = Attachment::new(filename.clone()).body(filebody, content_type);
        let email_builder = Message::builder()
        .from(email_configuration.from_address.parse().unwrap())
        .reply_to(email_configuration.from_address.parse().unwrap())
            .to(email.parse().unwrap())
            .subject("Experiment Notification")
            .header(ContentType::TEXT_PLAIN)
            .multipart(
                MultiPart::mixed()
                    .singlepart(
                        SinglePart::builder()
                            .header(ContentType::TEXT_HTML)
                            .body(String::from("Experimental Results Attached!")),
                    )
                    .singlepart(attachment),
            );

        let email = match email_builder {
            Ok(email) => email,
            Err(e) => {
                eprintln!("Could not build email: {e:?}");
                return;
            }
        };

        log::info!("{:?}", email_configuration.server);
        let mailer = match email_configuration.security {
            
            false => SmtpTransport::builder_dangerous(email_configuration.server).build(),
            true => {
                let creds = Credentials::new(
                    email_configuration.username.to_owned().expect("a secure email requires a username, have you set up proper STMP authentication?"),
                    email_configuration.password.to_owned().expect("a secure email requires a password, have you set up proper STMP authentication?"),
                );
                SmtpTransport::relay(&email_configuration.server)
                    .unwrap()
                    .credentials(creds)
                    .build()
            }
        };
        // Send the email
        match mailer.send(&email) {
            Ok(_) => println!("Email sent successfully!"),
            Err(e) => eprintln!("Could not send email: {e:?}"),
        }
    }
}
pub fn get_filename_from_path(path: &str) -> String {
    path.rsplit('/').next().unwrap_or("").to_string()
}
