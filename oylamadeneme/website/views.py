import random
import string
from flask import Blueprint, render_template, request, flash, redirect,url_for
from flask_login import login_required, current_user,logout_user
from .models import Group, Member,Poll, User,Vote
from .forms import GroupForm, OylamaForm
from . import db
import json
from .models import get_user_votes,get_user_groups


views = Blueprint('views', __name__)


@views.route('/')
@login_required
def home():
    return render_template("home.html", user=current_user)

def create_vote_code():
    return ''.join(random.choices(string.ascii_letters+string.digits,k=7))

@views.route('/create_group', methods=['GET', 'POST'])
@login_required
def create_group():
    form = GroupForm()
    if form.validate_on_submit():
        group_name = form.name.data
        new_group = Group(name=group_name)
        db.session.add(new_group)
        db.session.commit()
        
        # Kullanıcıyı gruba ekleyin
        new_member = Member(user_id=current_user.id, group_id=new_group.id)
        db.session.add(new_member)
        db.session.commit()
        
        flash('Grup başarıyla oluşturuldu!', category='success')
        return redirect(url_for('views.home'))
    
    return render_template('create_group.html', user=current_user, form=form)


@views.route('/create_poll', methods=['GET', 'POST'])
@login_required
def create_poll():
    form = OylamaForm()
    # Kullanıcının üye olduğu grupları çekiyoruz
    user_groups = Group.query.join(Member).filter(Member.user_id == current_user.id).all()
    form.group_id.choices = [(group.id, group.name) for group in user_groups]
    
    if form.validate_on_submit():
        question = form.question.data
        options = form.options.data.split('\n')
        group_id = form.group_id.data

        new_poll = Poll(question=question, options=json.dumps(options), group_id=group_id, created_by=current_user.id)
        db.session.add(new_poll)
        db.session.commit()

        vote_code = create_vote_code()
        flash(f"Anket başarıyla oluşturuldu! \nOylama Katılım Kodu: {vote_code}", category='success')
        
        available_polls = current_user.groups.polls
        available_polls.append(new_poll)
        
        return redirect(url_for('views.home'))
    
    return render_template('create_poll.html',user=current_user, form=form)

@views.route('/vote/<int:poll_id>', methods=['GET', 'POST'])
@login_required
def vote(poll_id):
    poll = Poll.query.get(poll_id)
    if request.method == 'POST':
        choice = request.form.get('choice') == 'yes'
        new_vote = Vote(user_id=current_user.id, poll_id=poll_id, choice=choice)
        db.session.add(new_vote)
        db.session.commit()
        flash('Oy başarıyla gönderildi!', category='success')
        return redirect(url_for('views.home'))
    return render_template("vote.html", user=current_user, poll=poll)

@views.route('/poll/<int:poll_id>/results')
@login_required
def view_results(poll_id):
    poll = Poll.query.get(poll_id)
    votes = Vote.query.filter_by(poll_id=poll_id).all()
    total_votes = len(votes)
    yes_votes = sum(1 for vote in votes if vote.choice)
    no_votes = total_votes - yes_votes

    poll.is_active = False  # Oylama sona erdi
    db.session.commit()

    # Oylama sonuçlarını gruptaki kullanıcılara bildirin
    group_members = Member.query.filter_by(group_id=poll.group_id).all()
    for member in group_members:
        user = User.query.get(member.user_id)
        flash(f'Oylama Sonuçları:\nEvet: {yes_votes}\nHayır: {no_votes}', category='info')  # Bu kısmı kullanıcıya e-posta ile gönderme vb. yapabilirsiniz.

    return render_template("poll_results.html", user=current_user, poll=poll, total_votes=total_votes, yes_votes=yes_votes, no_votes=no_votes)


@views.route('/polls')
@login_required
def list_polls():
    # Kullanıcının üye olduğu grupların ID'lerini al
    user_group_ids = [group.id for group in current_user.groups]

    # Kullanıcının üye olduğu gruplardaki oylamaları al
    available_polls = Poll.query.filter(Poll.group_id.in_(user_group_ids)).all()
    
    return render_template("polls.html", user=current_user, polls=available_polls)

@views.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))