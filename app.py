from flask import Flask, render_template, request, redirect, url_for
import sqlite3, os
import numpy as np
import pandas as pd
from astropy.table import Table


app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
app.config['SERVER_NAME'] = None


def init_db():
	mdb = sqlite3.connect('motherload')
	cur=mdb.cursor()
	cur.execute(""" 
		CREATE TABLE IF NOT EXISTS saved_superevents (
		superid text PRIMARY KEY,
		triggertime real,
		triggers text,
		events text,
		obsid text,
		t90_czt real,
		t90_veto real,
		status text
		);
		""")
	cur.execute("""CREATE TABLE IF NOT EXISTS diagnostics (
		eventid text PRIMARY KEY,
		triggertime real, 
		obsid text, 
		orbit text, 
		binning real,
		method text, 
		rankb0Q0 real,rankb0Q1 real, rankb0Q2 real, rankb0Q3 real, 
		rankb1Q0 real,rankb1Q1 real, rankb1Q2 real, rankb1Q3 real, 
		rankb2Q0 real,rankb2Q1 real, rankb2Q2 real, rankb2Q3 real);""")
	cols=cur.execute("PRAGMA table_info (superevents)").fetchall()
	if (len(cols)==5):
		cur.execute("ALTER TABLE superevents ADD COLUMN status text")
	mdb.commit()
	return mdb

def fetch_superevent_data(superid):
	try:
		txtf = open('static/pdffiles/'+superid+'/stats.txt','r').readlines()
		bestbin = float(txtf[2].split()[1])
		statcsv = Table.read('static/pdffiles/'+superid+'/statfile.csv')
		statcsv = statcsv[statcsv['binning size'] == bestbin]
		if(bestbin == 0.1):
			t90_czt = np.array(np.round(statcsv['t90'],2))[0]
			t90_veto = -100
		else:
			t90_czt =  np.array(np.round(statcsv[statcsv['lctype']=='czti']['t90'],2))[0]
			t90_veto = np.array(np.round(statcsv[statcsv['lctype']=='veto']['t90'],2))[0]
	except:
		txtf = []
		bestbin = 1.0	
		t90_czt = -100
		t90_veto = -100
	return txtf, bestbin, t90_czt, t90_veto

@app.route('/home', methods=['POST','GET'])
def home():
	mdb=init_db()
	cur=mdb.cursor()
	cur.execute("SELECT status from statuslist")
	statlist=cur.fetchall()
	if request.method == 'POST':
		sf=sdate[:4]+sdate[5:7]+sdate[-2:]
		edate = request.form['enddate']
		ef=edate[:4]+edate[5:7]+edate[-2:]		
		evttype = request.form['evttype']
		return redirect(url_for('scan_superevents',sdate=sdate,edate=edate,evttype=evttype))
		#elif (request.form["action"]=="Get_Diagnostics"):

#			return redirect(url_for('get_diagnostics'))
	return render_template('homepage.html',statlist=statlist)




@app.route('/scan_superevents?sdate=<sdate>&edate=<edate>&evttype=<evttype>', methods = ['POST', 'GET'])
def scan_superevents(sdate,edate,evttype):
	print(sdate)

	#connect to database
	mdb = init_db()
	cur = mdb.cursor()
	newedate = str(int(edate) + 1)

	if(evttype == 'none'):
		cur.execute(" SELECT * FROM superevents WHERE obsid BETWEEN '"+sdate+"%' AND '"+newedate+"%' AND status IS NULL ; ")
	else:
		cur.execute("SELECT id FROM statuslist WHERE status='"+evttype+"'")
		statid=str(np.array(cur.fetchall()[0])[0])
		cur.execute(" SELECT * FROM superevents WHERE obsid BETWEEN '"+sdate+"%' AND '"+newedate+"%' AND status LIKE '%"+statid+"%' ; ")
	sevents = np.array(cur.fetchall())
	superevents = []
	for se in sevents:
		superid = se[0]
		txtf, bestbin, t90_czt, t90_veto = fetch_superevent_data(superid)
		snapcztpath = 'pdffiles/'+se[0]+'/snap_czti_'+str(se[1])+'_'+str(bestbin)+'_.png'
		snapvetopath = 'pdffiles/'+se[0]+'/snap_veto_'+str(se[1])+'_'+str(bestbin)+'_.png'
		line = {'superid':se[0],'triggertime':se[1],'numevents':len(se[3].split(',')),'snapczt':snapcztpath,
				'snapveto':snapvetopath,'stattxt':txtf,'t90czt':t90_czt,'t90veto':t90_veto}
		superevents.append(line)
		#print(superid)
	
	##check if status column exists in superevents table, if not add
	if(request.method == 'POST'):
		res = request.form.getlist('Discard')
		#print(res)
		for sid in res:
			#print(sid)
			cur.execute("SELECT * FROM superevents WHERE superid = '"+sid+"';")
			#print(cur.fetchall())
			cur.execute("UPDATE superevents SET status = '1' WHERE superid = '"+sid+"'")
			#cur.execute("SELECT status FROM superevents WHERE superid = '"+sid+"';")
			#print(cur.fetchall())
			mdb.commit()
		return redirect(url_for('scan_superevents',sdate=sdate,edate=edate,evttype=evttype))
		# if(request.form['action'] == 'Save'):
		# 	sid = request.form['Superid']
		# 	sid_ind = np.where(sevents[:,0] == sid)[0][0]
		# 	#call_function_to_save_in_mdb_savetable
		# 	cur.execute("UPDATE superevents SET status = '"+request.form['tag']+"' WHERE superid = '"+sid+"'")
		# 	line = sevents[sid_ind][0:5]
		# 	newline = np.array([superevents[sid_ind]['t90czt'],superevents[sid_ind]['t90veto'],request.form['tag']])
		# 	line = np.concatenate([line,newline])
		# 	print (line)
		# 	cur.execute("""INSERT OR IGNORE INTO saved_superevents (superid, triggertime, triggers, events, obsid, 
		# 				t90_czt, t90_veto, status) VALUES (?,?,?,?,?,?,?,?) """ , line)
		# 	mdb.commit()
		# elif(request.form['action'] == 'Discard'):
		# 	sid = request.form['Superid']
		# 	#print sid
		# 	cur.execute("UPDATE superevents SET status = 'discarded' WHERE superid = '"+sid+"'")
		# 	mdb.commit()
	return render_template('scantest2.html',sdate=sdate,edate=edate,superevents=superevents)

@app.route('/add_tag',methods=['POST','GET'])
def add_tag():
	mdb = sqlite3.connect('motherload')
	cur = mdb.cursor()
	cur.execute("SELECT id,status from statuslist")
	statlist=cur.fetchall()
	
	if request.method=='POST':
		newtag=request.form['tagname']
		for item in statlist:
			if newtag==item[1]:
				return("ALREADY THERE YOU IDIOT!")
		cur.execute("""INSERT INTO statuslist (status) VALUES ('"""+newtag+"""')""")
		mdb.commit()
		return render_template('add_tag.html',statlist=statlist)

	return render_template('add_tag.html',statlist=statlist)


@app.route('/inspect_<superevent_id>',methods=['POST', 'GET'])
def inspect(superevent_id):
	mdb = sqlite3.connect('motherload')
	cur = mdb.cursor()
	cur.execute("SELECT id,status from statuslist")
	statlist=np.asarray(cur.fetchall())
	superevent = np.array(cur.execute("SELECT * FROM superevents WHERE superid = '"+superevent_id+"'").fetchall())[0]
	events = superevent[3].split(',')
	preid=np.array(cur.execute("SELECT superid,triggertime FROM superevents WHERE triggertime<"+str(superevent[1])+" ORDER BY triggertime DESC").fetchall())[0][0]
	#print(preid)
	postid=np.array(cur.execute("SELECT superid,triggertime FROM superevents WHERE triggertime>"+str(superevent[1])+" ORDER BY triggertime ").fetchall())[0][0]
	#print(postid)
	eventlist = np.array(cur.execute("SELECT * FROM events WHERE eventid IN ('"+"','".join(events)+"')").fetchall())
	superdir = 'static/pdffiles/'+superevent_id+'/'
	if (request.method=='POST'):
			print ("1")
			if(request.form['action'] == 'Save'):
				sid = request.form['Superid']
				#sid_ind = np.where(sevents[:,0] == sid)[0][0]
				#call_function_to_save_in_mdb_savetable
				evttype=request.form.getlist('add_tag')
				print(evttype)
				eid=''
				for evt in evttype:
					#print(evt)
					eid=eid+evt
				print(eid)
				cur.execute("UPDATE superevents SET status = '"+eid+"' WHERE superid = '"+sid+"'")
				line=np.array(cur.execute("SELECT superid,triggertime,triggers,events,obsid FROM superevents where superid= '"+sid+"'").fetchall())[0]
			 	# line=np.array(cur.execute("SELECT superid,triggertime,triggers,events,obsid FROM superevents where superid= '"+sid+"'").fetchall())[0]
				print(line)
				txtf, bestbin, t90_czt, t90_veto = fetch_superevent_data(sid)	
				newline=[t90_czt,t90_veto,eid]
				line = np.concatenate([line,newline])
				print (line)
				cur.execute("""INSERT OR IGNORE INTO saved_superevents (superid, triggertime, triggers, events, obsid, t90_czt, t90_veto, status) VALUES (?,?,?,?,?,?,?,?) """ , line)
				mdb.commit()
				return redirect(url_for('inspect',superevent_id = postid))
				
			elif(request.form['action'] == 'Discard'):
				sid = request.form['Superid']
				cur.execute("UPDATE superevents SET status = '1' WHERE superid = '"+sid+"'")
				mdb.commit()
				return redirect(url_for('inspect',superevent_id = postid))
			elif(request.form['action'] == 'Previous'):
				return redirect(url_for('inspect',superevent_id = preid))
			elif(request.form['action'] == 'Next'):
				return redirect(url_for('inspect',superevent_id = postid))
	try:
		txtf, bestbin, t90_czt, t90_veto = fetch_superevent_data(superevent_id)
		snaps = [superdir+'snap_czti_'+str(superevent[1])+'_0.1_.png',superdir+'snap_czti_'+str(superevent[1])+'_1.0_.png',
				superdir+'snap_czti_'+str(superevent[1])+'_10.0_.png',superdir+'snap_veto_'+str(superevent[1])+'_1.0_.png',
				superdir+'snap_veto_'+str(superevent[1])+'_10.0_.png']
		pdfs_czti = [superdir+str(superevent[1])+'_0.1_lightcurves_czti.pdf',superdir+str(superevent[1])+'_1.0_lightcurves_czti.pdf',
					 superdir+str(superevent[1])+'_10.0_lightcurves_czti.pdf']
		pdfs_veto = [superdir+str(superevent[1])+'_1.0_lightcurves_veto.pdf',superdir+str(superevent[1])+'_10.0_lightcurves_veto.pdf']
		pdfs = np.concatenate([pdfs_czti,pdfs_veto])
		for x,snap in enumerate(snaps):
			snaps[x] = os.path.basename(snap)
		for x,pdf in enumerate(pdfs):
			pdfs[x] = os.path.basename(pdf)
		imgs = zip(snaps, pdfs)
		statcsv = pd.read_csv(superdir+'statfile.csv')
		statcsv['bg'] = np.round(statcsv['bg'],2)
		statcsv['	rate'] = np.round(statcsv['rate'],2)
		statcsv['counts'] = np.round(statcsv['counts'],2)
		statcsv['t90'] = np.round(statcsv['t90'],2)
		orbit=statcsv['orbit'][0]
		statcsv = np.array(statcsv)
		pd.set_option('display.max_colwidth', -1)
		
		line = {'superid':superevent_id, 'triggers':superevent[2], 'obsid':superevent[4], 'status':superevent[5],
				'stattxt':txtf, 'statcsv':statcsv, 'imgs':imgs, 'eventlist':eventlist}
	except:
		return "No data available! Check manually"
	
	return render_template('inspecttest.html', data=line,statlist=statlist)

# @app.route('/mdb?sdate=<sdate>&edate=<edate>&evttype=<evttype>', methods = ['POST', 'GET'])
# def mdb(sdate,edate,evttype):
# 	mdb = init_db()
# 	cur = mdb.cursor()
# 	cur.execute(" SELECT * FROM superevents WHERE obsid BETWEEN '"+sdate+"%' AND '"+edate+"%' AND status = '"+evttype+"' ; ")
# 	sevents=cur.fetchall()
# 	print(sevents)
# 	return render_template('date.html',sevents=sevents)
#@app.route('/<asd>')
# def index(asd):
# 	return '<h1>Hello {}</h1>'.format(asd)

# @app.route('/theform') ,sdate=sdate,edate=edate,superevents=superevents
# def theform():
# 	return '''<form method="POST" action='/form2'>
# 				<input type="text" name="name">
# 				<input type="text" name="location">
# 				<input type="submit" value="Submit">
# 				</form>'''

# @app.route('/form2', methods=["POST"])
# def form2():
# 	name=request.form['name']
# 	location=request.form['location']
# 	return '<h1> Hi {}, You are in {}'.format(name, location)
# @app.route('/query')
# def query():
# 	name = request.args.get('name')
# 	location = request.args.get('location')
	# return "<h1> Hi {}!, You are from {}. This is the query page".format(name, location)

if __name__ == "__main__":
    socketio.run(app)
