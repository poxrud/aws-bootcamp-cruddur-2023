import './ProfileForm.css';
import React from "react";
import process from 'process';
import { getAccessToken } from 'lib/CheckAuth';

import FormErrors from 'components/FormErrors';
import { post } from 'lib/Requests';

export default function ProfileForm(props) {
  const [bio, setBio] = React.useState('');
  const [displayName, setDisplayName] = React.useState('');
  const [errors, setErrors] = React.useState([]);

  React.useEffect(() => {
    setBio(props.profile.bio || '');
    setDisplayName(props.profile.display_name);
  }, [props.profile])

  const s3uploadkey = async (extension) => {
    console.log('ext', extension)
    try {
      const gateway_url = `${process.env.REACT_APP_API_GATEWAY_ENDPOINT_URL}/avatars/key_upload`
      const access_token = await getAccessToken();
      const json = {
        extension: extension
      }
      console.log("ORIGIN: ", process.env.REACT_APP_FRONTEND_URL);
      const res = await fetch(gateway_url, {
        method: "POST",
        body: JSON.stringify(json),
        headers: {
          'Authorization': `Bearer ${access_token}`,
          'Accept': 'application/json',
          'Content-Type': 'application/json'
        }
      })
      let data = await res.json();
      if (res.status === 200) {
        return data.url
      } else {
        console.log(res)
      }
    } catch (err) {
      console.log(err);
    }
  }
  const s3upload = async (event) => {
    console.log('event', event)
    const file = event.target.files[0]
    const filename = file.name
    const size = file.size
    const type = file.type
    // const preview_image_url = URL.createObjectURL(file)
    console.log(filename, size, type)
    const fileparts = filename.split('.')
    const extension = fileparts[fileparts.length - 1]
    const presignedurl = await s3uploadkey(extension)
    // return;
    try {
      console.log('s3upload')
      const res = await fetch(presignedurl, {
        method: "PUT",
        body: file,
        headers: {
          'Content-Type': type
        }
      })
      if (res.status === 200) {

      } else {
        console.log(res)
      }
    } catch (err) {
      console.log(err);
    }
  }

  const onsubmit = async (event) => {
    event.preventDefault();

    const backend_url = `${process.env.REACT_APP_BACKEND_URL}/api/profile/update`
    const payload_data = {
      bio: bio,
      display_name: displayName
    };

    await post(backend_url,
      payload_data,
      {
        auth: true,
        setErrors: setErrors,
        success: (data) => {
          setBio(null)
          setDisplayName(null)
          props.setPopped(false)
        }
      }
    );
  }

  const bio_onchange = (event) => {
    setBio(event.target.value);
  }

  const display_name_onchange = (event) => {
    setDisplayName(event.target.value);
  }

  const close = (event) => {
    if (event.target.classList.contains("profile_popup")) {
      props.setPopped(false)
    }
  }

  if (props.popped === true) {
    return (
      <div className="popup_form_wrap profile_popup" onClick={close}>
        <form
          className='profile_form popup_form'
          onSubmit={onsubmit}
        >
          <div className="popup_heading">
            <div className="popup_title">Edit Profile</div>
            <div className='submit'>
              <button type='submit'>Save</button>
            </div>
          </div>
          <div className="popup_content">
            <input type="file" name="avatarupload" onChange={s3upload} />

            <div className="field display_name">
              <label>Display Name</label>
              <input
                type="text"
                placeholder="Display Name"
                value={displayName}
                onChange={display_name_onchange}
              />
            </div>
            <div className="field bio">
              <label>Bio</label>
              <textarea
                placeholder="Bio"
                value={bio}
                onChange={bio_onchange}
              />
            </div>
            <FormErrors errors={errors} />
          </div>
        </form>
      </div>
    );
  }
}