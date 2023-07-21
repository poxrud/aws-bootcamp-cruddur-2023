import "./MessageForm.css";
import React from "react";
import process from "process";
import { useParams } from "react-router-dom";
import FormErrors from "components/FormErrors";
import { post } from 'lib/Requests';

export default function ActivityForm(props) {
  const [count, setCount] = React.useState(0);
  const [message, setMessage] = React.useState("");
  const [errors, setErrors] = React.useState([]);
  const params = useParams();

  const classes = [];
  classes.push("count");
  if (1024 - count < 0) {
    classes.push("err");
  }

  const onsubmit = async (event) => {
    event.preventDefault();
    const backend_url = `${process.env.REACT_APP_BACKEND_URL}/api/messages`;

    let json = { message: message };
    if (params.handle) {
      json.handle = params.handle;
    } else {
      json.message_group_uuid = params.message_group_uuid;
    }

    await post(backend_url, json, {
      auth: true,
      setErrors: setErrors,
      success: function (data) {
        if (data.message_group_uuid) {
          console.log("redirect to message group");
          window.location.href = `/messages/${data.message_group_uuid}`;
        } else {
          props.setMessages((current) => [...current, data]);
        }
      }
    });
  };

  const textarea_onchange = (event) => {
    setCount(event.target.value.length);
    setMessage(event.target.value);
  };

  return (
    <form className="message_form" onSubmit={onsubmit}>
      <textarea
        type="text"
        placeholder="send a direct message..."
        value={message}
        onChange={textarea_onchange}
      />
      <div className="submit">
        <div className={classes.join(" ")}>{1024 - count}</div>
        <button type="submit">Message</button>
      </div>
      <FormErrors errors={errors} />
    </form>
  );
}
