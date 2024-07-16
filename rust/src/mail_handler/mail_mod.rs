
use lettre::message::{header::ContentType, Attachment, MultiPart, SinglePart};
use lettre::{Message, SmtpTransport, Transport};
use std::path::PathBuf;
use std::fs;


pub fn mailer(email_adr: Option<&String>, file_path: &PathBuf, file_name: &String) {
    match email_adr {
        Some(email) => {
            let filename = file_name;
            let filebody =
                fs::read(file_path)
                    .expect("Cant find file!");
            let content_type = ContentType::parse("text/plain").unwrap();
            let attachment = Attachment::new(filename.clone()).body(filebody, content_type);
            let email_builder = Message::builder()
                .from("PyFeX <PyFex@canterbury.ac.nz>".parse().unwrap())
                .reply_to("PyFeX <PyFex@canterbury.ac.nz>".parse().unwrap())
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

            let mailer = SmtpTransport::builder_dangerous("smtphost.canterbury.ac.nz").build();

            // Send the email
            match mailer.send(&email) {
                Ok(_) => println!("Email sent successfully!"),
                Err(e) => eprintln!("Could not send email: {e:?}"),
            }
        }
        None => {
            // Do nothing if no email address is provided
        }
    }
}