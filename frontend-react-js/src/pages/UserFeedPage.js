import './UserFeedPage.css';
import React, { useEffect } from "react";
import { useParams } from 'react-router-dom';

import DesktopNavigation from 'components/DesktopNavigation';
import DesktopSidebar from 'components/DesktopSidebar';
import ActivityFeed from 'components/ActivityFeed';
import ActivityForm from 'components/ActivityForm';
import ProfileHeading from 'components/ProfileHeading';
import ProfileForm from 'components/ProfileForm';


import { checkAuth } from 'lib/CheckAuth';
import { get } from 'lib/Requests';

export default function UserFeedPage() {
  const [activities, setActivities] = React.useState([]);
  const [profile, setProfile] = React.useState([]);
  const [popped, setPopped] = React.useState([]);
  const [poppedProfile, setPoppedProfile] = React.useState([]);
  const [user, setUser] = React.useState(null);
  const dataFetchedRef = React.useRef(false);

  const params = useParams();

  useEffect(() => {
    async function loadData(params) {
      const backend_url = `${process.env.REACT_APP_BACKEND_URL}/api/activities/@${params.handle}`

      await get(backend_url, {
        auth: false,
        success: (data) => {
          console.log('setprofile', data.profile)
          setProfile(data.profile)
          setActivities(data.activities)
        }
      });
    };

    //prevents double call
    if (dataFetchedRef.current) return;

    loadData(params);
    checkAuth(setUser);

    dataFetchedRef.current = true;
  }, [params])

  return (
    <article>
      <DesktopNavigation user={user} active={'profile'} setPopped={setPopped} />
      <div className='content'>
        <ActivityForm popped={popped} setActivities={setActivities} />
        <ProfileForm
          profile={profile}
          popped={poppedProfile}
          setPopped={setPoppedProfile}
        />
        <div className='activity_feed'>
          <ProfileHeading setPopped={setPoppedProfile} profile={profile} />
          <ActivityFeed activities={activities} />
        </div>
      </div>
      <DesktopSidebar user={user} />
    </article>
  );
}